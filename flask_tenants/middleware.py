from werkzeug.wrappers import Request
from werkzeug.exceptions import abort
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import g, request, Blueprint, jsonify
import logging

from .context import clear_schema_renamed

logger = logging.getLogger(__name__)

DEFAULT_TENANT_URL_PREFIX = '/StrangeWomenLyingInPondsDistributingSwordsIsNoBasisForASystemOfGovernment'


class URLRewriteMiddleware:
    def __init__(self, app, base_domain, non_tenant_domains=None, tenant_url_prefix=DEFAULT_TENANT_URL_PREFIX):
        self.app = app
        self.base_domain = base_domain.strip().lower()
        self.non_tenant_domains = []
        if non_tenant_domains:
            for domain in non_tenant_domains:
                self.non_tenant_domains.append(domain.strip().lower())
        self.tenant_url_prefix = tenant_url_prefix

    def __call__(self, environ, start_response):
        req = Request(environ)
        host = req.host.split(':')[0].strip().lower()  # Extract host without port

        if host not in self.non_tenant_domains and host != self.base_domain:
            environ['PATH_INFO'] = f'{self.tenant_url_prefix}{req.path}'

        return self.app(environ, start_response)


class MultiTenancyMiddleware:
    def __init__(self, app, base_domain, db, default_schema='public', tenant_url_prefix=DEFAULT_TENANT_URL_PREFIX):
        self.app = app
        self.base_domain = base_domain.strip().lower()
        self.db = db
        self.default_schema = default_schema
        self.tenant_url_prefix = tenant_url_prefix

        if self.db is None:
            raise ValueError('Database instance must be provided')

        app.before_request(self._before_request_func)
        app.teardown_request(self._teardown_request_func)

    def _get_tenant_from_host(self, host):
        if host == self.base_domain:
            return None
        if host.endswith('.' + self.base_domain):
            tenant_index = len(self.base_domain.split('.')) + 1
            tenant_name = host.split('.')[-tenant_index]
            # TODO validate tenant name specifically here
            return tenant_name
        domain_object = g.db_session.query(self.db.Model.Domain).filter_by(domain_name=host).first()
        if domain_object:
            return domain_object.tenant_name
        return None

    def _before_request_func(self):
        g.db_session = scoped_session(sessionmaker(bind=self.db.engine))()
        g.tenant = self._get_tenant_from_host(request.host.split(':')[0].strip().lower()) or self.default_schema
        print(g.tenant)
        g.tenant_scoped = g.tenant != self.default_schema
        if g.tenant != self.default_schema:
            tenant_object = g.db_session.query(self.db.Model.Tenant).filter_by(name=g.tenant).first()
            if tenant_object is None:
                logger.debug(f'Tenant \'{g.tenant}\' not found.')
                abort(jsonify(message='Tenant not found'), 404)

            if hasattr(tenant_object, 'deactivated') and tenant_object.deactivated:
                abort(jsonify(message='Tenant deactivated'), 404)

    def _teardown_request_func(self, exception=None):
        clear_schema_renamed()
        g.db_session.close()

    def create_tenant_blueprint(self, name):
        return Blueprint(name, __name__, url_prefix=self.tenant_url_prefix)

    def create_public_blueprint(self, name):
        return Blueprint(name, __name__)


def create_tenancy(app, base_domain, db, non_tenant_domains=None, tenant_url_prefix=DEFAULT_TENANT_URL_PREFIX):
    url_rewrite_middleware = URLRewriteMiddleware(app.wsgi_app, base_domain, non_tenant_domains, tenant_url_prefix)
    app.wsgi_app = url_rewrite_middleware
    multi_tenancy_middleware = MultiTenancyMiddleware(app, base_domain, db, tenant_url_prefix=tenant_url_prefix)
    return multi_tenancy_middleware
