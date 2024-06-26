from .middleware import MultiTenancyMiddleware, create_tenancy
from .utils import create_tenant, get_tenant, update_tenant, delete_tenant
from .models import BaseTenant, BaseDomain, db


def init_app(app, tenant_model=None, domain_model=None):
    db.init_app(app)

    # Register custom models if provided
    if tenant_model:
        setattr(db.Model, 'Tenant', tenant_model)
    if domain_model:
        setattr(db.Model, 'Domain', domain_model)


__all__ = ['init_app', 'create_tenant', 'get_tenant', 'update_tenant', 'delete_tenant', 'BaseTenant', 'BaseDomain',
           'create_tenancy']
