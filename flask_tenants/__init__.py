from .middleware import MultiTenancyMiddleware, create_tenancy
from .models import BaseTenant, BaseDomain, db
from .utils import register_event_listeners, register_engine_event_listeners
from .exceptions import (TenantActivationError,
                         TenantNotFoundError,
                         SchemaRenameError,
                         SchemaCreationError,
                         SchemaDropError,
                         TableCreationError
                         )


def init_app(app, tenant_model=None, domain_model=None):
    db.init_app(app)

    if tenant_model:
        setattr(db.Model, 'Tenant', tenant_model)
    if domain_model:
        setattr(db.Model, 'Domain', domain_model)

    with app.app_context():
        register_event_listeners()
        register_engine_event_listeners(db.engine)


__all__ = ['init_app',
           'BaseTenant',
           'BaseDomain',
           'create_tenancy',
           'TenantActivationError',
           'TenantNotFoundError',
           'SchemaRenameError',
           'SchemaCreationError',
           'SchemaDropError',
           'TableCreationError'
           ]
