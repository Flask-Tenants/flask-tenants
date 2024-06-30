import logging
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker, Session, attributes
from sqlalchemy.sql import text
from .models import db

logging.basicConfig(level=logging.DEBUG)


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
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        with session.connection() as conn:
            conn.execute(text(f'SET search_path TO "{schema_name}"'))
            db.Model.metadata.create_all(conn)
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to create tables: {e}")
    finally:
        session.close()


def rename_schema(old_name, new_name):
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        session.execute(text(f'ALTER SCHEMA "{old_name}" RENAME TO "{new_name}"'))
        session.commit()
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to rename schema: {e}")
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
        for instance in session.new:
            if tenant_model and isinstance(instance, tenant_model):
                create_schema(instance.name)
                create_tables(instance.name)
            else:
                pass

        for instance in session.dirty:
            if tenant_model and isinstance(instance, tenant_model):
                history = attributes.get_history(instance, 'name')
                if history.has_changes():
                    old_name = history.deleted[0]  # Get the original name before the update
                    try:
                        rename_schema(old_name, instance.name)
                    except RuntimeError as e:
                        print(f"[before_flush] Skipping schema rename due to error: {e}")

                    # Update tenant entry in public table
                    session.execute(text(f'UPDATE tenants SET name = :new_name WHERE name = :old_name').bindparams(
                        new_name=instance.name, old_name=old_name))
                    session.execute(
                        text(f'UPDATE domains SET tenant_name = :new_name WHERE tenant_name = :old_name').bindparams(
                            new_name=instance.name, old_name=old_name))
            else:
                pass

        for instance in session.deleted:
            if tenant_model and isinstance(instance, tenant_model):
                schema_name = instance.name  # Get the current name
                drop_schema(schema_name)
            else:
                pass


register_event_listeners()
