# C:\users\cory\test_tenants_app\flask_tenants\utils.py
import logging
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.sql import text
from .models import db

logging.basicConfig(level=logging.DEBUG)


def create_schema(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        logging.debug(f"[create_schema] Attempting to create schema: {schema_name}")
        session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        session.commit()
        logging.debug(f"[create_schema] Schema {schema_name} created successfully")
    except Exception as e:
        session.rollback()
        logging.error(f"[create_schema] Failed to create schema {schema_name}: {e}")
        raise RuntimeError(f"Failed to create schema: {e}")
    finally:
        session.close()
        logging.debug(f"[create_schema] Session closed for schema creation: {schema_name}")


def create_tables(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        logging.debug(f"[create_tables] Attempting to create tables in schema: {schema_name}")
        with session.connection() as conn:
            conn.execute(text(f'SET search_path TO {schema_name}'))
            db.Model.metadata.create_all(conn)
        logging.debug(f"[create_tables] Tables created successfully in schema {schema_name}")
    except Exception as e:
        session.rollback()
        logging.error(f"[create_tables] Failed to create tables in schema {schema_name}: {e}")
        raise RuntimeError(f"Failed to create tables: {e}")
    finally:
        session.close()
        logging.debug(f"[create_tables] Session closed for table creation: {schema_name}")


def rename_schema(old_name, new_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        logging.debug(f"[rename_schema] Attempting to rename schema from {old_name} to {new_name}")
        session.execute(text(f'ALTER SCHEMA "{old_name}" RENAME TO "{new_name}"'))
        session.commit()
        logging.debug(f"[rename_schema] Schema {old_name} renamed to {new_name} successfully")
    except Exception as e:
        session.rollback()
        logging.error(f"[rename_schema] Failed to rename schema from {old_name} to {new_name}: {e}")
        raise RuntimeError(f"Failed to rename schema: {e}")
    finally:
        session.close()
        logging.debug(f"[rename_schema] Session closed for schema renaming from {old_name} to {new_name}")


def drop_schema(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        logging.debug(f"[drop_schema] Attempting to drop schema: {schema_name}")
        session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        session.commit()
        logging.debug(f"[drop_schema] Schema {schema_name} dropped successfully")
    except Exception as e:
        session.rollback()
        logging.error(f"[drop_schema] Failed to drop schema {schema_name}: {e}")
    finally:
        session.close()
        logging.debug(f"[drop_schema] Session closed for schema dropping: {schema_name}")


def register_event_listeners():
    logging.debug("[register_event_listeners] Registering event listeners")

    @event.listens_for(Session, 'before_flush')
    def before_flush(session, flush_context, instances):
        for instance in session.new:
            Tenant = getattr(db.Model, 'Tenant', None)
            logging.debug(f"[before_flush] Event Listener 'before_flush' triggered for instance: {instance}")
            if Tenant and isinstance(instance, Tenant):
                logging.debug(f"[before_flush] Instance is a Tenant: {instance.name}")
                create_schema(instance.name)
                create_tables(instance.name)
            else:
                logging.debug(f"[before_flush] Skipping schema creation for non-tenant instance: {instance}")

    @event.listens_for(Session, 'before_update')
    def before_update(session, flush_context, instances):
        for instance in session.dirty:
            Tenant = getattr(db.Model, 'Tenant', None)
            logging.debug(f"[before_update] Event Listener 'before_update' triggered for instance: {instance}")
            if Tenant and isinstance(instance, Tenant):
                session = scoped_session(sessionmaker(bind=db.engine))()
                old_tenant = session.query(Tenant).filter(Tenant.name == instance.name).first()
                session.close()
                logging.debug(f"[before_update] Queried old tenant: {old_tenant}")
                if old_tenant and old_tenant.name != instance.name:
                    logging.debug(f"[before_update] Renaming schema from {old_tenant.name} to {instance.name}")
                    rename_schema(old_tenant.name, instance.name)
            else:
                logging.debug(f"[before_update] Skipping schema renaming for non-tenant instance: {instance}")

    @event.listens_for(Session, 'before_delete')
    def before_delete(session, flush_context, instances):
        for instance in session.deleted:
            Tenant = getattr(db.Model, 'Tenant', None)
            logging.debug(f"[before_delete] Event Listener 'before_delete' triggered for instance: {instance}")
            if Tenant and isinstance(instance, Tenant):
                logging.debug(f"[before_delete] Dropping schema for tenant: {instance.name}")
                drop_schema(instance.name)
            else:
                logging.debug(f"[before_delete] Skipping schema dropping for non-tenant instance: {instance}")

    logging.debug("[register_event_listeners] Event listeners registered")


register_event_listeners()
