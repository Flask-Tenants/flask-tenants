import logging
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql import text
from .models import db

# Set up logging
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
    logging.debug(f"Attempting to drop schema: {schema_name}")
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        result = session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        session.commit()
        logging.debug(f"Successfully dropped schema: {schema_name}, result: {result}")
    except Exception as e:
        session.rollback()
        logging.error(f"Failed to drop schema: {e}")
        raise RuntimeError(f"Failed to drop schema: {e}")
    finally:
        session.close()


def register_event_listeners():
    @event.listens_for(db.Model, 'before_insert')
    def before_insert(mapper, connection, target):
        if isinstance(target, db.Model) and hasattr(target, 'name'):
            logging.debug(f"Triggered before_insert for tenant: {target.name}")
            create_schema(target.name)

    @event.listens_for(db.Model, 'before_update')
    def before_update(mapper, connection, target):
        if isinstance(target, db.Model) and hasattr(target, 'name'):
            logging.debug(f"Triggered before_update for tenant: {target.name}")
            old_tenant = db.session.query(type(target)).get(target.name)
            if old_tenant and old_tenant.name != target.name:
                rename_schema(old_tenant.name, target.name)

    @event.listens_for(db.Model, 'before_delete')
    def before_delete(mapper, connection, target):
        if isinstance(target, db.Model) and hasattr(target, 'name'):
            logging.debug(f"Triggered before_delete for tenant: {target.name}")
            drop_schema(target.name)

    logging.debug("Event listeners registered")


register_event_listeners()
