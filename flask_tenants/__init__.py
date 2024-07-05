from .middleware import MultiTenancyMiddleware, create_tenancy, FlaskTenants
from .models import BaseTenant, BaseDomain, db
from .utils import register_event_listeners, register_engine_event_listeners
from .exceptions import (TenantActivationError, TenantNotFoundError, SchemaRenameError, SchemaCreationError,
                         SchemaDropError, TableCreationError)


def init_app(app, tenant_model=None, domain_model=None):
    flask_tenants = FlaskTenants(app, tenant_model, domain_model, db)
    flask_tenants.init()


__all__ = ['init_app', 'BaseTenant', 'BaseDomain', 'create_tenancy', 'FlaskTenants', 'TenantActivationError',
           'TenantNotFoundError', 'SchemaRenameError', 'SchemaCreationError', 'SchemaDropError', 'TableCreationError']
