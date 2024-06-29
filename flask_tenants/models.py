from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class BaseTenant(db.Model):
    __abstract__ = True
    name = db.Column(db.String(128), primary_key=True, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


class BaseDomain(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)  # Primary key for the domain
    tenant_name = db.Column(db.String(128), db.ForeignKey('tenants.name'), nullable=False)
    domain_name = db.Column(db.String(255), unique=True, nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)


