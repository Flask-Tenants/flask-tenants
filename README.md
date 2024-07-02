# Flask Tenants

Flask Tenants is a Flask extension for multi-tenancy support using subdomains and SQLAlchemy schemas. The `MultiTenancyMiddleware` extracts the tenant from the request host and switches the database schema accordingly. If no tenant is extracted, it defaults to the public schema.

## Installation

```bash
pip install flask-tenants
```

## Database Preparation

1. Create a new PostgreSQL database (if not already created):

```sql
CREATE DATABASE flask_tenants;
```

1. Connect to the database and create the public schema and extension for UUID generation:

```sql
\c flask_tenants
CREATE SCHEMA IF NOT EXISTS public;
```

1. Ensure your database user has the necessary privileges to create schemas:

```sql
GRANT ALL PRIVILEGES ON DATABASE "flask_tenants" to your_user;
```

## Usage

### Basic Setup

Create a Flask application and initialize SQLAlchemy. Set up the multi-tenancy middleware.

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_tenants import MultiTenancyMiddleware
from flask_tenants import init_app as tenants_init_app, create_tenancy
from public.models import Tenant, Domain


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/dbname'
db = SQLAlchemy(app)

# Initialize the tenancy
tenants_init_app(app, tenant_model=Tenant, domain_model=Domain)

# Set up tenancy middleware
tenancy = create_tenancy(app, db, tenant_url_prefix='/_tenant')
```

#### tenant_url_prefix

This is optional, but the default is quite long. It is recommended to set this to a default value that will not be used in any other route. The module uses this on the backend to route tenant-scoped requests and handles it invisibly to prevent the need for a */tenant/* route prefixing all tenant-scoped requests.

### Models

#### Tenancy models

Define your tenant and domain models by inheriting from `BaseTenant` and `BaseDomain`.

```python
from flask_tenants import BaseTenant, BaseDomain, db

class Tenant(BaseTenant):
    __tablename__ = 'tenants'
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    deactivated = db.Column(db.Boolean(), nullable=False, default=False)

class Domain(BaseDomain):
    __tablename__ = 'domains'
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    tenant_name = db.Column(db.String(128), nullable=False)
    domain_name = db.Column(db.String(255), unique=True, nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
```

#### BaseTenant

`BaseTenant` provides *name*, *created_at*, and *updated_at* attributes.

```python
class BaseTenant(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)  # Ensure unique constraint
    name = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())
```

#### BaseDomain

`BaseDomain` provides *tenant_name*, *domain_name*, and *is_primary* attributes.

```python
class BaseDomain(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_name = db.Column(db.String(128), db.ForeignKey('tenants.name'), nullable=False)
    domain_name = db.Column(db.String(255), unique=True, nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
```

#### BaseTenantModel

`BaseTenantModel` provides no attributes.

```python
class BaseTenantModel(db.Model):
    __abstract__ = True
    __table_args__ = ({'schema': 'tenant'})
```

#### Tenant Deactivation
If you'd like to be able to deactivate a tenant without deleting it, 
for example if a SaaS customer forgets to pay their bill, you can optionally
add a `deactivated` field to your tenant model:

```python
class Tenant(BaseTenant):
    __tablename__ = 'tenants'
    # ...
    deactivated = db.Column(db.Boolean(), nullable=False, default=False)
```

Flask-Tenants will check if this field exists early in the request lifecycle and abort 
the request early with a 404 if it is `True`.

### Tenant scoped models

Define tenant scoped models by inheriting from `BaseTenantModel` and setting the proper `info` table argument.

```python
from flask_tenants.models import db, BaseTenantModel


class Tank(BaseTenantModel):
    __abstract__ = False
    __tablename__ = 'tanks'
    __table_args__ = {'info': {'tenant_specific': True}}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=True)
    capacity = db.Column(db.Float, nullable=True)
    location = db.Column(db.String(255), nullable=True)
```

## Implementing CRUD Operations

The `with_db()` utility must be used for all tenant-scoped database accesses for search_path schema to automatically apply.

```python
from flask_tenants.utils import with_db

with with_db() as session:
    tank = session.query(Tank).filter_by(id=tank_id).first()
```

### Sample app.py

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from flask_tenants import init_app as tenants_init_app, create_tenancy, db
from public.models import Tenant, Domain
from public.routes import public_bp
from tenants.routes import tenant_bp
from tanks.routes import tank_bp

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = Flask(__name__)
app.config.from_object('config.Config')

# Initialize Flask-Tenants with custom models
tenants_init_app(app, tenant_model=Tenant, domain_model=Domain)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Set up tenancy middleware
tenancy = create_tenancy(app, db, tenant_url_prefix='/_tenant')

# Create blueprints
root_public_bp = tenancy.create_public_blueprint('public')
root_tenant_bp = tenancy.create_tenant_blueprint('tenant')
root_tank_bp = tenancy.create_tenant_blueprint('tank')

root_public_bp.register_blueprint(public_bp)
root_tenant_bp.register_blueprint(tenant_bp)
root_tank_bp.register_blueprint(tank_bp)

app.register_blueprint(root_public_bp)
app.register_blueprint(root_tenant_bp)
app.register_blueprint(root_tank_bp)

if __name__ == '__main__':
    app.run(debug=True)
```


