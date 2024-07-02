from contextvars import ContextVar

schema_already_renamed = ContextVar('schema_already_renamed', default=False)


def set_schema_renamed():
    schema_already_renamed.set(True)


def is_schema_renamed():
    return schema_already_renamed.get()


def clear_schema_renamed():
    schema_already_renamed.set(False)
