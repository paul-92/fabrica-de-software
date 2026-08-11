"""Canonical persistence contracts for Quality Gate results."""

from asep.quality_results.errors import (
    DuplicateQualityGateResultError,
    InvalidQualityGateResultStorageFormatError,
    QualityGateResultStorageError,
    QualityGateResultStorageReadError,
    QualityGateResultStorageWriteError,
)
from asep.quality_results.in_memory import InMemoryQualityGateResultRepository
from asep.quality_results.file_repository import FileQualityGateResultRepository
from asep.quality_results.models import StoredQualityGateResult
from asep.quality_results.repository import QualityGateResultRepository
from asep.quality_results.sqlite_repository import SQLiteQualityGateResultRepository

__all__ = [
    "DuplicateQualityGateResultError",
    "FileQualityGateResultRepository",
    "InMemoryQualityGateResultRepository",
    "InvalidQualityGateResultStorageFormatError",
    "QualityGateResultRepository",
    "QualityGateResultStorageError",
    "QualityGateResultStorageReadError",
    "QualityGateResultStorageWriteError",
    "SQLiteQualityGateResultRepository",
    "StoredQualityGateResult",
]
