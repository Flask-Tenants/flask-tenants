class SchemaCreationError(Exception):
    pass


class TableCreationError(Exception):
    pass


class SchemaRenameError(Exception):
    pass


class SchemaDropError(Exception):
    pass


class TenantActivationError(Exception):
    pass


class TenantNotFoundError(Exception):
    pass