"""API pública do domínio e repositório de Runs."""

from asep.runs.errors import (
    InvalidRunStorageFormatError,
    RunStorageError,
    RunStorageReadError,
    RunStorageWriteError,
)
from asep.runs.file_repository import FileRunRepository
from asep.runs.in_memory import InMemoryRunRepository
from asep.runs.models import Run, RunError, RunStatus
from asep.runs.repository import RunRepository
from asep.runs.sqlite_repository import SQLiteRunRepository

__all__ = [
    "FileRunRepository",
    "InMemoryRunRepository",
    "InvalidRunStorageFormatError",
    "Run",
    "RunError",
    "RunRepository",
    "RunStatus",
    "RunStorageError",
    "RunStorageReadError",
    "RunStorageWriteError",
    "SQLiteRunRepository",
]
