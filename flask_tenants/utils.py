import logging
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker, Session, attributes
from sqlalchemy.sql import text
from .models import db

logging.basicConfig(level=logging.DEBUG)


def create_schema(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        print(f"[create_schema] Attempting to create schema: {schema_name}")
        logging.debug(f"[create_schema] Attempting to create schema: {schema_name}")
        session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        session.commit()
        print(f"[create_schema] Schema {schema_name} created successfully")
        logging.debug(f"[create_schema] Schema {schema_name} created successfully")
    except Exception as e:
        session.rollback()
        print(f"[create_schema] Failed to create schema {schema_name}: {e}")
        logging.error(f"[create_schema] Failed to create schema {schema_name}: {e}")
        raise RuntimeError(f"Failed to create schema: {e}")
    finally:
        session.close()
        print(f"[create_schema] Session closed for schema creation: {schema_name}")
        logging.debug(f"[create_schema] Session closed for schema creation: {schema_name}")


def create_tables(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        print(f"[create_tables] Attempting to create tables in schema: {schema_name}")
        logging.debug(f"[create_tables] Attempting to create tables in schema: {schema_name}")
        with session.connection() as conn:
            conn.execute(text(f'SET search_path TO "{schema_name}"'))
            db.Model.metadata.create_all(conn)
        print(f"[create_tables] Tables created successfully in schema {schema_name}")
        logging.debug(f"[create_tables] Tables created successfully in schema {schema_name}")
    except Exception as e:
        session.rollback()
        print(f"[create_tables] Failed to create tables in schema {schema_name}: {e}")
        logging.error(f"[create_tables] Failed to create tables in schema {schema_name}: {e}")
        raise RuntimeError(f"Failed to create tables: {e}")
    finally:
        session.close()
        print(f"[create_tables] Session closed for table creation: {schema_name}")
        logging.debug(f"[create_tables] Session closed for table creation: {schema_name}")


def rename_schema(old_name, new_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        print(f"[rename_schema] Attempting to rename schema from {old_name} to {new_name}")
        logging.debug(f"[rename_schema] Attempting to rename schema from {old_name} to {new_name}")
        session.execute(text(f'ALTER SCHEMA "{old_name}" RENAME TO "{new_name}"'))
        session.commit()
        print(f"[rename_schema] Schema {old_name} renamed to {new_name} successfully")
        logging.debug(f"[rename_schema] Schema {old_name} renamed to {new_name} successfully")
    except Exception as e:
        session.rollback()
        print(f"[rename_schema] Failed to rename schema from {old_name} to {new_name}: {e}")
        logging.error(f"[rename_schema] Failed to rename schema from {old_name} to {new_name}: {e}")
        raise RuntimeError(f"Failed to rename schema: {e}")
    finally:
        session.close()
        print(f"[rename_schema] Session closed for schema renaming from {old_name} to {new_name}")
        logging.debug(f"[rename_schema] Session closed for schema renaming from {old_name} to {new_name}")


def drop_schema(schema_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        print(f"[drop_schema] Attempting to drop schema: {schema_name}")
        logging.debug(f"[drop_schema] Attempting to drop schema: {schema_name}")
        session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        session.commit()
        print(f"[drop_schema] Schema {schema_name} dropped successfully")
        logging.debug(f"[drop_schema] Schema {schema_name} dropped successfully")
    except Exception as e:
        session.rollback()
        print(f"[drop_schema] Failed to drop schema {schema_name}: {e}")
        logging.error(f"[drop_schema] Failed to drop schema {schema_name}: {e}")
    finally:
        session.close()
        print(f"[drop_schema] Session closed for schema dropping: {schema_name}")
        logging.debug(f"[drop_schema] Session closed for schema dropping: {schema_name}")


def register_event_listeners():
    print("[register_event_listeners] Registering event listeners")
    logging.debug("[register_event_listeners] Registering event listeners")

    @event.listens_for(Session, 'before_flush')
    def before_flush(session, flush_context, instances):
        print("[before_flush] Event Listener 'before_flush' triggered")
        logging.debug("[before_flush] Event Listener 'before_flush' triggered")

        Tenant = getattr(db.Model, 'Tenant', None)
        for instance in session.new:
            print(f"[before_flush] New instance: {instance}")
            logging.debug(f"[before_flush] Event Listener 'before_flush' triggered for new instance: {instance}")
            if Tenant and isinstance(instance, Tenant):
                print(f"[before_flush] Instance is a Tenant: {instance.name}")
                logging.debug(f"[before_flush] Instance is a Tenant: {instance.name}")
                create_schema(instance.name)
                create_tables(instance.name)
            else:
                print(f"[before_flush] Skipping schema creation for non-tenant instance: {instance}")
                logging.debug(f"[before_flush] Skipping schema creation for non-tenant instance: {instance}")

        for instance in session.dirty:
            print(f"[before_flush] Dirty instance: {instance}")
            logging.debug(f"[before_flush] Event Listener 'before_flush' triggered for dirty instance: {instance}")
            if Tenant and isinstance(instance, Tenant):
                history = attributes.get_history(instance, 'name')
                if history.has_changes():
                    old_name = history.deleted[0]  # Get the original name before the update
                    print(f"[before_flush] Old name: {old_name}, New name: {instance.name}")
                    logging.debug(f"[before_flush] Old name: {old_name}, New name: {instance.name}")
                    try:
                        rename_schema(old_name, instance.name)
                    except RuntimeError as e:
                        print(f"[before_flush] Skipping schema rename due to error: {e}")
                        logging.debug(f"[before_flush] Skipping schema rename due to error: {e}")

                    # Update tenant entry in public table
                    session.execute(text(f'UPDATE tenants SET name = :new_name WHERE name = :old_name').bindparams(
                        new_name=instance.name, old_name=old_name))
                    session.execute(
                        text(f'UPDATE domains SET tenant_name = :new_name WHERE tenant_name = :old_name').bindparams(
                            new_name=instance.name, old_name=old_name))
            else:
                print(f"[before_flush] Skipping schema renaming for non-tenant instance: {instance}")
                logging.debug(f"[before_flush] Skipping schema renaming for non-tenant instance: {instance}")

        for instance in session.deleted:
            print(f"[before_flush] Deleted instance: {instance}")
            logging.debug(f"[before_flush] Event Listener 'before_flush' triggered for deleted instance: {instance}")
            if Tenant and isinstance(instance, Tenant):
                schema_name = instance.name  # Get the current name
                print(f"[before_flush] Dropping schema for tenant: {schema_name}")
                logging.debug(f"[before_flush] Dropping schema for tenant: {schema_name}")
                drop_schema(schema_name)
            else:
                print(f"[before_flush] Skipping schema dropping for non-tenant instance: {instance}")
                logging.debug(f"[before_flush] Skipping schema dropping for non-tenant instance: {instance}")

    @event.listens_for(Session, 'after_flush')
    def after_flush(session, flush_context):
        print("[after_flush] Event Listener 'after_flush' triggered")
        logging.debug("[after_flush] Event Listener 'after_flush' triggered")

        Tenant = getattr(db.Model, 'Tenant', None)
        for instance in session.dirty:
            print(f"[after_flush] Dirty instance: {instance}")
            logging.debug(f"[after_flush] Event Listener 'after_flush' triggered for dirty instance: {instance}")
            if Tenant and isinstance(instance, Tenant):
                print(f"[after_flush] Instance is a Tenant: {instance.name}")
                logging.debug(f"[after_flush] Instance is a Tenant: {instance.name}")
            else:
                print(f"[after_flush] Skipping post-flush logic for non-tenant instance: {instance}")
                logging.debug(f"[after_flush] Skipping post-flush logic for non-tenant instance: {instance}")

    print("[register_event_listeners] Event listeners registered")
    logging.debug("[register_event_listeners] Event listeners registered")


register_event_listeners()
