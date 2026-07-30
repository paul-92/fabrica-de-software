"""Erros da infraestrutura SQLite compartilhada."""

from asep.errors import AsepError


class SQLiteStorageError(AsepError):
    code = "SQLITE_STORAGE_ERROR"
    category = "persistence"
    next_action = "Verifique o caminho, permissões e integridade do SQLite."
    exit_code = 5


class SQLiteConnectionError(SQLiteStorageError):
    code = "SQLITE_CONNECTION_ERROR"


class SQLiteSchemaError(SQLiteStorageError):
    code = "SQLITE_SCHEMA_INVALID"
    category = "validation"
    next_action = (
        "Preserve o banco inválido e restaure um schema SQLite compatível."
    )
    exit_code = 3
