from .middleware import MultiTenancyMiddleware, create_tenancy
from .models import BaseTenant, BaseDomain, db
from .utils import register_event_listeners


def init_app(app, tenant_model=None, domain_model=None):
    db.init_app(app)

    if tenant_model:
        setattr(db.Model, 'Tenant', tenant_model)
    if domain_model:
        setattr(db.Model, 'Domain', domain_model)

    register_event_listeners()  # Ensure this is called


__all__ = ['init_app', 'BaseTenant', 'BaseDomain', 'create_tenancy']
