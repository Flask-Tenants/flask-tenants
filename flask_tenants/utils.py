from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql import text
from .models import db


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
    session = scoped_session(sessionmaker(bind=db.engine))()
    try:
        session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        session.commit()
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to drop schema: {e}")
    finally:
        session.close()


@event.listens_for(db.Model, 'before_insert')
def before_insert(mapper, connection, target):
    if isinstance(target, db.Model.Tenant):
        create_schema(target.name)


@event.listens_for(db.Model, 'before_update')
def before_update(mapper, connection, target):
    if isinstance(target, db.Model.Tenant):
        old_tenant = db.session.query(db.Model.Tenant).get(target.id)
        if old_tenant.name != target.name:
            rename_schema(old_tenant.name, target.name)


@event.listens_for(db.Model, 'before_delete')
def before_delete(mapper, connection, target):
    if isinstance(target, db.Model.Tenant):
        drop_schema(target.name)
