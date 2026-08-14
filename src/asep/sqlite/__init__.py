"""Infraestrutura SQLite compartilhada."""

from asep.sqlite.database import SCHEMA_VERSION, SQLiteDatabase
from asep.sqlite.errors import (
    SQLiteConnectionError,
    SQLiteSchemaError,
    SQLiteStorageError,
)

__all__ = [
    "SCHEMA_VERSION",
    "SQLiteConnectionError",
    "SQLiteDatabase",
    "SQLiteSchemaError",
    "SQLiteStorageError",
]
