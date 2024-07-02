import logging
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker, Session, attributes
from sqlalchemy.sql import text
from .models import db
from flask import g

logging.basicConfig(level=logging.DEBUG)


@contextmanager
def with_db(database=db):
    if g.tenant_scoped:
        schema_translate_map = dict(tenant=g.tenant)
    else:
        schema_translate_map = None
    connectable = database.engine.execution_options(schema_translate_map=schema_translate_map)
    session = Session(autocommit=False, autoflush=False, bind=connectable)
    try:
        yield session
    finally:
        session.close()


def create_schema(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        session.commit()
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to create schema: {e}")
    finally:
        session.close()


def create_tables(schema_name):
    with with_db(database=db) as session:
        try:
            session.execute(text(f'SET search_path TO "{schema_name}", public'))
            metadata = db.Model.metadata

            tables_to_create = []
            for table in metadata.tables.values():
                if table.info.get('tenant_specific'):
                    table.schema = schema_name
                    tables_to_create.append(table)

            metadata.create_all(bind=session.bind, tables=tables_to_create)
        except Exception as e:
            session.rollback()
            raise RuntimeError(f"Failed to create tables: {e}")
        finally:
            session.close()


def create_public_tables():
    with with_db(database=db) as session:
        try:
            session.execute(text('SET search_path TO public'))
            db.Model.metadata.create_all(bind=session.bind, tables=[
                db.Model.metadata.tables['tenants'],
                db.Model.metadata.tables['domains']
            ])
        except Exception as e:
            session.rollback()
            raise RuntimeError(f"Failed to create public tables: {e}")
        finally:
            session.close()


def create_schema_and_tables(schema_name):
    try:
        create_schema(schema_name)
        create_public_tables()
        create_tables(schema_name)
    except RuntimeError as e:
        raise


def rename_schema_and_update_tables(old_name, new_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        session.execute(text(f'ALTER SCHEMA "{old_name}" RENAME TO "{new_name}"'))
        session.execute(text(f'UPDATE tenants SET name = :new_name WHERE name = :old_name').bindparams(
            new_name=new_name, old_name=old_name))
        session.execute(text(f'UPDATE domains SET tenant_name = :new_name WHERE tenant_name = :old_name').bindparams(
            new_name=new_name, old_name=old_name))
        session.commit()
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to rename schema and update tables: {e}")
    finally:
        session.close()


def drop_schema(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()


def register_event_listeners():
    @event.listens_for(Session, 'before_flush')
    def before_flush(session, flush_context, instances):
        tenant_model = getattr(db.Model, 'Tenant', None)
        session._already_renamed = getattr(session, '_already_renamed', set())

        for instance in session.new:
            if tenant_model and isinstance(instance, tenant_model):
                create_schema_and_tables(instance.name)

        for instance in session.dirty:
            if tenant_model and isinstance(instance, tenant_model):
                history = attributes.get_history(instance, 'name')
                if history.has_changes():
                    old_name = history.deleted[0]
                    new_name = instance.name
                    if old_name != new_name and old_name not in session._already_renamed:
                        try:
                            rename_schema_and_update_tables(old_name, new_name)
                            session._already_renamed.add(old_name)
                        except RuntimeError as e:
                            logging.error(f"Error renaming schema before flush: {e}")
                            raise

    @event.listens_for(Session, 'after_flush')
    def after_flush(session, flush_context):
        tenant_model = getattr(db.Model, 'Tenant', None)

        for instance in session.dirty:
            if tenant_model and isinstance(instance, tenant_model):
                history = attributes.get_history(instance, 'name')
                if history.has_changes():
                    new_name = instance.name
                    if new_name in session._already_renamed:
                        session._already_renamed.remove(new_name)

        for instance in session.deleted:
            if tenant_model and isinstance(instance, tenant_model):
                schema_name = instance.name
                drop_schema(schema_name)


register_event_listeners()