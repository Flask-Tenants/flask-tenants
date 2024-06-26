# Flask Tenants

Flask Tenants is a Flask extension for multi-tenancy support using subdomains and SQLAlchemy schemas. The `MultiTenancyMiddleware` extracts the tenant from the request host and switches the database schema accordingly. If no tenant is extracted, it defaults to the public schema.

## Installation

Install using pip:

```bash
pip install flask-tenants
```

## Usage

### Basic Setup

1. Create a Flask application and initialize SQLAlchemy.
2. Set up the multitenancy middleware.

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

## Tenant Management

The `flask_tenants.utils` module provides several functions to manage tenants:

- `create_tenant`: Create a new tenant
- `delete_tenant`: Delete an existing tenant
- `get_tenant`: Fetch details of a specific tenant
- `get_all_tenants`: Fetch details of all tenants
- `update_tenant`: Update details of an existing tenant

## Examples

### Create a Tenant

```python
from flask_tenants.utils import create_tenant

new_tenant = create_tenant({
    "name": "tenant_name",
    "domain_name": "tenant_name.local.test",
    "phone_number": "123-456-7890",
    "address": "123 Example St"
})
print(new_tenant)
```

### Delete a Tenant

```python
from flask_tenants.utils import delete_tenant

success = delete_tenant(tenant_id)
print(success)
```

### Get a Tenant

```python
from flask_tenants.utils import get_tenant

tenant = get_tenant(tenant_id)
print(tenant)
```

### Get All Tenants

```python
from flask_tenants.utils import get_all_tenants

tenants = get_all_tenants()
print(tenants)
```

### Update a Tenant

```python
from flask_tenants.utils import update_tenant

updated_tenant = update_tenant(tenant_id, {
    "name": "new_tenant_name",
    "phone_number": "987-654-3210",
    "address": "456 Updated St"
})
print(updated_tenant)
```

## Full Example

### app.py

```python
from flask import Flask, g, request, Blueprint, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from flask_tenants import init_app as tenants_init_app, create_tenancy, create_tenant, get_tenant, update_tenant, delete_tenant, db
from myapp.models import Tenant, Domain

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = Flask(__name__)
app.config.from_object('myapp.config.DefaultConfig')

# Initialize Flask-Tenants with custom models
tenants_init_app(app, tenant_model=Tenant, domain_model=Domain)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Set up tenancy middleware
tenancy = create_tenancy(app, db, tenant_url_prefix='/_tenant')

# Create blueprints
public_bp = tenancy.create_public_blueprint('public')
tenant_bp = tenancy.create_tenant_blueprint('tenant')

# Define routes for public blueprint
@public_bp.route('/')
def public_index():
    return 'Welcome to the public index page!'

# Define routes for tenant blueprint
@tenant_bp.route('/test')
def tenant_test():
    tenant = g.tenant if hasattr(g, 'tenant') else 'unknown'
    return f'Welcome to the tenant index page for {tenant}!'

# Demonstration of utility functions
@public_bp.route('/create_tenant', methods=['POST'])
def create_tenant_route():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid input data"}), 400

    try:
        tenant = create_tenant(data)
        return jsonify({"message": f"Tenant {tenant.name} created successfully", "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "phone_number": tenant.phone_number,
            "address": tenant.address
        }}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@public_bp.route('/get_tenant/<int:tenant_id>', methods=['GET'])
def get_tenant_route(tenant_id):
    try:
        tenant = get_tenant(tenant_id)
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404
        return jsonify({"id": tenant.id, "name": tenant.name, "phone_number": tenant.phone_number, "address": tenant.address}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@public_bp.route('/update_tenant/<int:tenant_id>', methods=['PUT'])
def update_tenant_route(tenant_id):
    data = request.json
    if not data:
        return jsonify({"error": "Invalid input data"}), 400

    try:
        tenant = update_tenant(tenant_id, data)
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
        success = delete_tenant(tenant_id)
        if success:
            return jsonify({"message": "Tenant deleted successfully"}), 200
        else:
            return jsonify({"error": "Tenant not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Register blueprints
app.register_blueprint(public_bp)
app.register_blueprint(tenant_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
```

### Configuration

### `config.py`

```python
class DefaultConfig:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/postgres'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

### Models

### `models.py`

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

### Running the Application

### `run.py`

```python
from myapp.app import app

if __name__ == '__main__':
    app.run(debug=True)
```

### Testing the Application

### `test-web.py`

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
        tenant_data = response.json().get('tenant')  # Ensure 'tenant' key exists in response
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
        tenant_data = response_data.get('tenant')  # Ensure 'tenant' key exists in response
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
    # Generate random tenants
    tenants = [generate_random_tenant(), generate_random_tenant()]

    created_tenants = []

    # Create tenants
    for tenant in tenants:
        created_tenant = create_tenant(tenant)
        if created_tenant:
            created_tenants.append(created_tenant)

    # Read tenants
    for tenant in created_tenants:
        get_tenant(tenant['id'])

    # Update tenants
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

    # Delete tenants
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