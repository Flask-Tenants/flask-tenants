from werkzeug.wrappers import Request
from werkzeug.exceptions import abort
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql import text
from flask import g, request, Blueprint
import logging
from .models import db

logger = logging.getLogger(__name__)

DEFAULT_TENANT_URL_PREFIX = '/StrangeWomenLyingInPondsDistributingSwordsIsNoBasisForASystemOfGovernment'


class URLRewriteMiddleware:
    def __init__(self, app, non_tenant_subdomains=None, tenant_url_prefix=DEFAULT_TENANT_URL_PREFIX):
        self.app = app
        self.non_tenant_subdomains = non_tenant_subdomains or ['www', 'localhost', 'local']
        self.tenant_url_prefix = tenant_url_prefix

    def __call__(self, environ, start_response):
        req = Request(environ)
        host = req.host.split(':')[0]  # Extract host without port

        if '.' in host and host.split('.')[0] not in self.non_tenant_subdomains:
            subdomain = host.split('.')[0]
            environ['PATH_INFO'] = f'{self.tenant_url_prefix}{req.path}'
            environ['HTTP_X_TENANT'] = subdomain

        return self.app(environ, start_response)


class MultiTenancyMiddleware:
    def __init__(self, app, db, default_schema='public', tenant_url_prefix=DEFAULT_TENANT_URL_PREFIX):
        self.app = app
        self.db = db
        self.default_schema = default_schema
        self.tenant_url_prefix = tenant_url_prefix

        if self.db is None:
            raise ValueError("Database instance must be provided")

        app.before_request(self._before_request_func)
        app.teardown_request(self._teardown_request_func)

    def _before_request_func(self):
        tenant = request.headers.get('X-TENANT', self.default_schema)
        g.tenant = tenant
        self._switch_tenant_schema(tenant)

    def _teardown_request_func(self, exception=None):
        self._reset_schema()

    def _switch_tenant_schema(self, tenant):
        session = scoped_session(sessionmaker(bind=self.db.engine))()
        try:
            session.execute(text('SET search_path TO :schema'), {'schema': tenant})
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Tenant schema switch failed: {e}")
            abort(500, description="Tenant schema switch failed")
        finally:
            session.close()

    def _reset_schema(self):
        session = scoped_session(sessionmaker(bind=self.db.engine))()
        try:
            session.execute(text('SET search_path TO public'))
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Schema reset failed: {e}")
            abort(500, description="Schema reset failed")
        finally:
            session.close()

    def create_tenant_blueprint(self, name):
        return Blueprint(name, __name__, url_prefix=self.tenant_url_prefix)

    def create_public_blueprint(self, name):
        return Blueprint(name, __name__)


def create_tenancy(app, db, non_tenant_subdomains=None, tenant_url_prefix=DEFAULT_TENANT_URL_PREFIX):
    url_rewrite_middleware = URLRewriteMiddleware(app.wsgi_app, non_tenant_subdomains, tenant_url_prefix)
    app.wsgi_app = url_rewrite_middleware
    multi_tenancy_middleware = MultiTenancyMiddleware(app, db, tenant_url_prefix=tenant_url_prefix)
    return multi_tenancy_middleware
