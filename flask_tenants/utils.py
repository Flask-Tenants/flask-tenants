import logging as logger
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker, Session, attributes
from sqlalchemy.sql import text
from .models import db
from flask import g
from .exceptions import *

logger.basicConfig(level=logger.DEBUG)


def schema_exists(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        result = session.execute(text(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_name"
        ), {'schema_name': schema_name})
        return result.scalar() is not None
    finally:
        session.close()


def create_schema(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        if schema_exists(schema_name):
            raise SchemaAlreadyExistsError(f"Schema '{schema_name}' already exists")

        session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        session.commit()
        logger.info(f"Schema '{schema_name}' created successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create schema '{schema_name}': {e}")
        raise SchemaCreationError(f"Failed to create schema: {e}")
    finally:
        session.close()


def create_tables(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        session.execute(text(f'SET search_path TO "{schema_name}", public'))
        metadata = db.Model.metadata

        tables_to_create = []
        for table in metadata.tables.values():
            if table.info.get('tenant_specific'):
                table.schema = schema_name
                tables_to_create.append(table)

        metadata.create_all(bind=session.bind, tables=tables_to_create)
        logger.info(f"Tables created for schema '{schema_name}'")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create tables for schema '{schema_name}': {e}")
        raise TableCreationError(f"Failed to create tables: {e}")
    finally:
        session.close()


def create_public_tables():
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        session.execute(text('SET search_path TO public'))
        db.Model.metadata.create_all(bind=session.bind, tables=[
            db.Model.metadata.tables['tenants'],
            db.Model.metadata.tables['domains']
        ])
        logger.info("Public tables created successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create public tables: {e}")
        raise TableCreationError(f"Failed to create public tables: {e}")
    finally:
        session.close()


def create_schema_and_tables(schema_name):
    try:
        create_schema(schema_name)
        create_public_tables()
        create_tables(schema_name)
    except SchemaCreationError as e:
        logger.error(f"Schema creation error for '{schema_name}': {e}")
        raise
    except TableCreationError as e:
        logger.error(f"Table creation error for '{schema_name}': {e}")
        raise


def rename_schema_and_update_tables(old_name, new_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        if not schema_exists(old_name):
            raise SchemaDoesNotExistError(f"Schema '{old_name}' does not exist")

        if schema_exists(new_name):
            raise SchemaAlreadyExistsError(f"Schema '{new_name}' already exists")

        session.execute(text(f'ALTER SCHEMA "{old_name}" RENAME TO "{new_name}"'))
        session.execute(text(f'UPDATE tenants SET name = :new_name WHERE name = :old_name').bindparams(
            new_name=new_name, old_name=old_name))
        session.execute(text(f'UPDATE domains SET tenant_name = :new_name WHERE tenant_name = :old_name').bindparams(
            new_name=new_name, old_name=old_name))
        session.commit()
        logger.info(f"Schema renamed from '{old_name}' to '{new_name}' and updated tables")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to rename schema from '{old_name}' to '{new_name}': {e}")
        raise SchemaRenameError(f"Failed to rename schema and update tables: {e}")
    finally:
        session.close()


def drop_schema(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        if not schema_exists(schema_name):
            raise SchemaDoesNotExistError(f"Schema '{schema_name}' does not exist")

        session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        session.commit()
        logger.info(f"Schema '{schema_name}' dropped successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to drop schema '{schema_name}': {e}")
        raise SchemaDropError(f"Failed to drop schema: {e}")
    finally:
        session.close()


def register_event_listeners():
    @event.listens_for(Session, 'before_flush')
    def before_flush(session, flush_context, instances):
        tenant_model = getattr(db.Model, 'Tenant', None)
        session._already_renamed = getattr(session, '_already_renamed', set())

        for instance in session.new:
            if tenant_model and isinstance(instance, tenant_model):
                try:
                    create_schema_and_tables(instance.name)
                except (SchemaCreationError, TableCreationError) as e:
                    logger.error(f"Error creating schema and tables for new tenant '{instance.name}': {e}")
                    raise

        for instance in session.dirty:
            if tenant_model and isinstance(instance, tenant_model):
                history = attributes.get_history(instance, 'name')
                if history.has_changes():
                    old_name = history.deleted[0]
                    new_name = history.added[0]
                    if old_name != new_name and old_name not in session._already_renamed:
                        try:
                            rename_schema_and_update_tables(old_name, new_name)
                            session._already_renamed.add(old_name)
                        except SchemaRenameError as e:
                            logger.error(f"Error renaming schema before flush: {e}")
                            raise

    @event.listens_for(Session, 'after_flush')
    def after_flush(session, flush_context):
        tenant_model = getattr(db.Model, 'Tenant', None)

        for instance in session.dirty:
            if tenant_model and isinstance(instance, tenant_model):
                history = attributes.get_history(instance, 'name')
                if history.has_changes():
                    new_name = history.added[0]
                    if new_name in session._already_renamed:
                        session._already_renamed.remove(new_name)

        for instance in session.deleted:
            if tenant_model and isinstance(instance, tenant_model):
                schema_name = instance.name
                try:
                    drop_schema(schema_name)
                except SchemaDropError as e:
                    logger.error(f"Error dropping schema '{schema_name}': {e}")
                    raise


def register_engine_event_listeners(engine):
    @event.listens_for(engine, 'before_cursor_execute')
    def set_search_path(conn, cursor, statement, parameters, context, executemany):
        if hasattr(g, 'tenant_scoped') and g.tenant_scoped:
            schema = g.tenant
            cursor.execute(f'SET search_path TO {schema}, public')
            logger.debug(f"Set search_path to {schema}")
        else:
            cursor.execute('SET search_path TO public')
            logger.debug("Set search_path to public")
