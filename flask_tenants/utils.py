from flask_tenants.models import db
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import text


def create_tenant(fields, **kwargs):
    try:
        tenant_model = getattr(db.Model, 'Tenant', None)
        domain_model = getattr(db.Model, 'Domain', None)

        if not tenant_model or not domain_model:
            raise RuntimeError("Tenant or Domain model not found")

        tenant_name = fields.get('name')
        domain_name = fields.get('domain_name')

        if not tenant_name or not domain_name:
            raise ValueError("Both tenant_name and domain_name are required")

        # Delete existing tenant and domain if they exist
        existing_tenant = tenant_model.query.filter_by(name=tenant_name).first()
        if existing_tenant:
            delete_tenant(existing_tenant.id)

        existing_domain = domain_model.query.filter_by(domain_name=domain_name).first()
        if existing_domain:
            db.session.delete(existing_domain)
            db.session.commit()

        tenant_fields = {k: v for k, v in fields.items() if k != 'domain_name'}
        tenant_fields.update(kwargs)
        tenant = tenant_model(**tenant_fields)
        db.session.add(tenant)
        db.session.flush()  # Ensure tenant ID is generated

        # Create the schema for the tenant using the tenant name
        schema_name = tenant_name
        # Check if the schema already exists
        schema_exists = db.session.execute(
            text(f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{schema_name}'")).scalar()
        if schema_exists:
            raise RuntimeError(f"Schema '{schema_name}' already exists")

        db.session.execute(text(f'CREATE SCHEMA "{schema_name}"'))

        domain = domain_model(domain_name=domain_name, is_primary=True, tenant_id=tenant.id)
        db.session.add(domain)
        db.session.commit()

        return tenant
    except IntegrityError as e:
        db.session.rollback()
        raise RuntimeError(f"Failed to create tenant due to integrity error: {e}")
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Failed to create tenant: {e}")


def get_tenant(tenant_id):
    tenant_model = getattr(db.Model, 'Tenant', None)
    if not tenant_model:
        raise RuntimeError("Tenant model not found")
    return tenant_model.query.get(tenant_id)


def update_tenant(tenant_id, update_fields, **kwargs):
    tenant_model = getattr(db.Model, 'Tenant', None)
    if not tenant_model:
        raise RuntimeError("Tenant model not found")

    tenant = tenant_model.query.get(tenant_id)
    if tenant:
        try:
            if 'name' in update_fields:
                new_name = update_fields['name']
                # Check if the new schema name already exists
                schema_exists = (db.session.execute(
                    text(f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{new_name}'"))
                                 .scalar())
                if schema_exists:
                    raise RuntimeError(f"Schema '{new_name}' already exists")

                # Rename the schema
                old_name = tenant.name
                db.session.execute(text(f'ALTER SCHEMA "{old_name}" RENAME TO "{new_name}"'))
                tenant.name = new_name

            for key, value in {**update_fields, **kwargs}.items():
                if key != 'name':
                    setattr(tenant, key, value)

            db.session.commit()
            # Refresh tenant object to get updated data
            db.session.refresh(tenant)

            return tenant

        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Failed to update tenant: {e}")

    raise ValueError(f"Tenant with ID={tenant_id} not found")


def delete_tenant(tenant_id):
    try:
        tenant_model = getattr(db.Model, 'Tenant', None)
        domain_model = getattr(db.Model, 'Domain', None)
        if not tenant_model or not domain_model:
            raise RuntimeError("Tenant or Domain model not found")

        tenant = tenant_model.query.get(tenant_id)
        if tenant:
            schema_name = tenant.name

            # Delete associated domains first
            domain_model.query.filter_by(tenant_id=tenant.id).delete()
            db.session.commit()

            # Delete tenant
            db.session.delete(tenant)
            db.session.commit()

            # Drop the schema
            db.session.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
            db.session.commit()

            return True
        return False
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Failed to delete tenant: {e}")
