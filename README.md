# Flask Tenants

Flask Tenants is a Flask extension for multi-tenancy support using subdomains and SQLAlchemy schemas. The `MultiTenancyMiddleware` extracts the tenant from the request host and switches the database schema accordingly. If no tenant is extracted, it defaults to the public schema.

## Installation

Install Flask Tenants using pip:

```bash
pip install flask-tenants
```

## Database Preparation

Before using Flask-Tenants, you need to prepare your PostgreSQL database to support multiple schemas.

1. Create a new PostgreSQL database (if not already created):

```sql
CREATE DATABASE flask_tenants;
```

2. Connect to the database and create the public schema and extension for UUID generation:

```sql
\c flask_tenants
CREATE SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

3. Ensure your database user has the necessary privileges to create schemas:

```sql
ALTER USER your_user WITH SUPERUSER;
```

## Usage

### Basic Setup

1. Create a Flask application and initialize SQLAlchemy.
2. Set up the multi-tenancy middleware.

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_tenants import MultiTenancyMiddleware, create_tenancy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/dbname'
db = SQLAlchemy(app)

# Set up multi-tenancy
multi_tenancy = MultiTenancyMiddleware(app, db)
```

### Models

Define your tenant and domain models by inheriting from `BaseTenant` and `BaseDomain`.

```python
from flask_tenants import BaseTenant, BaseDomain, db

class Tenant(BaseTenant):
    __tablename__ = 'tenants'
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)

class Domain(BaseDomain):
    __tablename__ = 'domains'
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
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


### Initialization

Initialize the Flask-Tenants extension with custom models.

```python
from flask_tenants import init_app as tenants_init_app, create_tenancy
from myapp.models import Tenant, Domain

tenants_init_app(app, tenant_model=Tenant, domain_model=Domain)

# Set up tenancy middleware
tenancy = create_tenancy(app, db, tenant_url_prefix='/_tenant')
```

### Blueprints and Routes

Set up public and tenant-specific blueprints.

```python
public_bp = tenancy.create_public_blueprint('public')
tenant_bp = tenancy.create_tenant_blueprint('tenant')

@public_bp.route('/')
def public_index():
    return 'Welcome to the public index page!'

@tenant_bp.route('/')
def tenant_index():
    tenant = g.tenant if hasattr(g, 'tenant') else 'unknown'
    return f'Welcome to the tenant index page for {tenant}!'

app.register_blueprint(public_bp)
app.register_blueprint(tenant_bp)
```

## Implementing CRUD Operations

You need to implement your own CRUD operations for managing tenants. Below are examples of how to create, retrieve, update, and delete tenants. The Flask-Tenants extension uses SQLAlchemy hooks to handle schema management automatically when these operations are performed.

## Examples

### Create a Tenant

```python
from flask import request, jsonify
from test_app.models import Tenant, Domain
from test_app import db


@app.route('/create_tenant', methods=['POST'])
def create_tenant():
    data = request.json
    if not data:
        return jsonify({'error': 'Invalid input data'}), 400

    tenant = Tenant(
        name=data['name'],
        phone_number=data['phone_number'],
        address=data['address']
    )
    db.session.add(tenant)
    db.session.flush()  # Flush to get the tenant ID

    domain = Domain(
        domain_name=data['domain_name'],
        tenant_id=tenant.id,
        is_primary=True
    )
    db.session.add(domain)
    db.session.commit()

    return jsonify({'message': 'Tenant created successfully', 'tenant': tenant.to_dict()}), 201
```

### Retrieve a Tenant

```python
@app.route('/get_tenant/<int:tenant_id>', methods=['GET'])
def get_tenant(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404
    return jsonify(tenant.to_dict()), 200
```

### Update a Tenant

```python
@app.route('/update_tenant/<int:tenant_id>', methods=['PUT'])
def update_tenant(tenant_id):
    data = request.json
    if not data:
        return jsonify({'error': 'Invalid input data'}), 400

    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    tenant.name = data['name']
    tenant.phone_number = data['phone_number']
    tenant.address = data['address']
    db.session.commit()

    return jsonify({'message': 'Tenant updated successfully', 'tenant': tenant.to_dict()}), 200
```

### Delete a Tenant

```python
@app.route('/delete_tenant/<int:tenant_id>', methods=['DELETE'])
def delete_tenant(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    db.session.delete(tenant)
    db.session.commit()

    return jsonify({'message': 'Tenant deleted successfully'}), 200
```

## Full Example

### app.py

```python
from flask import Flask, g, request, Blueprint, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from flask_tenants import init_app as tenants_init_app, create_tenancy, db
from test_app.models import Tenant, Domain

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = Flask(__name__)
app.config.from_object('test_app.config.DefaultConfig')

# Initialize Flask-Tenants with custom models
tenants_init_app(app, tenant_model=Tenant, domain_model=Domain)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Set up tenancy middleware
tenancy = create_tenancy(app, db, tenant_url_prefix='/_tenant')

# Create blueprints
public_bp = tenancy.create_public_blueprint('public')
tenant_bp = tenancy.create_tenant_blueprint('tenant')


@public_bp.route('/')
def public_index():
    return 'Welcome to the public index page!'


@tenant_bp.route('/')
def tenant_index():
    tenant = g.tenant if hasattr(g, 'tenant') else 'unknown'
    return f'Welcome to the tenant index page for {tenant}!'


# Example CRUD Routes
@public_bp.route('/create_tenant', methods=['POST'])
def create_tenant_route():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid input data"}), 400

    tenant_data = {k: v for k, v in data.items() if k in Tenant.__table__.columns.keys()}
    domain_name = data.get('domain_name')
    if not domain_name:
        return jsonify({"error": "domain_name is required"}), 400

    tenant = Tenant(**tenant_data)
    db.session.add(tenant)
    db.session.flush()  # Flush to get the tenant ID

    domain = Domain(domain_name=domain_name, tenant_id=tenant.id, is_primary=True)
    db.session.add(domain)
    db.session.commit()

    return jsonify({"message": f"Tenant {tenant.name} created successfully", "tenant": {
        "id": tenant.id,
        "name": tenant.name,
        "phone_number": tenant.phone_number,
        "address": tenant.address
    }}), 201


@public_bp.route('/get_tenant/<int:tenant_id>', methods=['GET'])
def get_tenant_route(tenant_id):
    try:
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404
        return jsonify({
            "id": tenant.id,
            "name": tenant.name,
            "phone_number": tenant.phone_number,
            "address": tenant.address
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@public_bp.route('/update_tenant/<int:tenant_id>', methods=['PUT'])
def update_tenant_route(tenant_id):
    data = request.json
    if not data:
        return jsonify({"error": "Invalid input data"}), 400

    try:
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404

        for key, value in data.items():
            if key in Tenant.__table__.columns.keys():
                setattr(tenant, key, value)

        db.session.commit()
        return jsonify({
            "message": f"Tenant {tenant.name} updated successfully",
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "phone_number": tenant.phone_number,
                "address": tenant.address
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@public_bp.route('/delete_tenant/<int:tenant_id>', methods=['DELETE'])
def delete_tenant_route(tenant_id):
    try:
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404

        db.session.delete(tenant)
        db.session.commit()
        return jsonify({"message": "Tenant deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


app.register_blueprint(public_bp)
app.register_blueprint(tenant_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
```

## Configuration

### config.py

```python
class DefaultConfig:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/postgres'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

### models.py

```python
from flask_tenants import BaseTenant, BaseDomain, db

class Tenant(BaseTenant):
    __tablename__ = 'tenants'
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)

class Domain(BaseDomain):
    __tablename__ = 'domains'
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)

    def __repr__(self):
        return f'<Domain {self.domain_name} (Primary: {self.is_primary})>'
```

### run.py

```python
from myapp.app import app

if __name__ == '__main__':
    app.run(debug=True)
```

### test-web.py

```python
import requests
import random
import json

BASE_URL = "http://localhost:5000"

def generate_random_tenant():
    number = random.randint(1000, 9999)
    name = f"tenant{number}"
    domain = f"{name}.local.test"
    phone = f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    address = f"{random.randint(100, 999)} Example St, City, Country"
    return {
        "name": name,
        "domain_name": domain,
        "phone_number": phone,
        "address": address
    }

def create_tenant(tenant):
    try:
        response = requests.post(f"{BASE_URL}/create_tenant", json=tenant)
        response.raise_for_status()
        tenant_data = response.json().get('tenant')
        if tenant_data:
            print(f"Created Tenant: ID={tenant_data['id']}, Name={tenant_data['name']}, "
                  f"Phone={tenant_data['phone_number']}, Address={tenant_data['address']}")
            return tenant_data
        else:
            raise ValueError("Failed to create tenant: Response does not contain 'tenant' key")
    except requests.RequestException as e:
        print(f"Error creating tenant {tenant['name']}: {e}")
    except ValueError as ve:
        print(str(ve))

def get_tenant(tenant_id):
    try:
        response = requests.get(f"{BASE_URL}/get_tenant/{tenant_id}")
        response.raise_for_status()
        tenant_data = response.json()
        print(f"Retrieved Tenant: ID={tenant_data['id']}, Name={tenant_data['name']}, "
              f"Phone={tenant_data['phone_number']}, Address={tenant_data['address']}")
        return tenant_data
    except requests.RequestException as e:
        print(f"Error retrieving tenant with ID {tenant_id}: {e}")

def update_tenant(tenant_id, update_fields):
    try:
        response = requests.put(f"{BASE_URL}/update_tenant/{tenant_id}", json=update_fields)
        response.raise_for_status()
        response_data = response.json()
        tenant_data = response_data.get('tenant')
        if tenant_data:
            print(f"Updated Tenant: ID={tenant_data['id']}, Name={tenant_data['name']}, "
                  f"Phone={tenant_data['phone_number']}, Address={tenant_data['address']}")
            return tenant_data
        else:
            raise ValueError("Failed to update tenant: Response does not contain 'tenant' key")
    except requests.RequestException as e:
        print(f"Error updating tenant with ID {tenant_id}: {e}")
    except ValueError as ve:
        print(str(ve))

def delete_tenant(tenant_id):
    try:
        response = requests.delete(f"{BASE_URL}/delete_tenant/{tenant_id}")
        response.raise_for_status()
        print(f"Deleted Tenant: ID={tenant_id}")
    except requests.RequestException as e:
        print(f"Error deleting tenant with ID {tenant_id}: {e}")

if __name__ == "__main__":
    tenants = [generate_random_tenant(), generate_random_tenant()]

    created_tenants = []

    for tenant in tenants:
        created_tenant = create_tenant(tenant)
        if created_tenant:
            created_tenants.append(created_tenant)

    for tenant in created_tenants:
        get_tenant(tenant['id'])

    updated_tenants = []
    for tenant in created_tenants:
        new_name = f"{tenant['name']}_updated"
        new_phone = f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        new_address = f"{random.randint(100, 999)} Updated St, City, Country"
        update_fields = {
            "name": new_name,
            "phone_number": new_phone,
            "address": new_address
        }
        updated_tenant = update_tenant(tenant['id'], update_fields)
        if updated_tenant:
            updated_tenants.append(updated_tenant)

    for tenant in updated_tenants:
        delete_tenant(tenant['id'])
```

## Configuration File

### `.env`

```
DATABASE_URI=postgresql://postgres:postgres@localhost/postgres
SECRET_KEY=your_secret_key
FLASK_DEBUG=true
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000
```

