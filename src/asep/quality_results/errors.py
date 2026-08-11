"""Errors raised by Quality Gate result persistence."""

from asep.errors import AsepError


class QualityGateResultStorageError(AsepError):
    code = "QUALITY_GATE_RESULT_STORAGE_ERROR"
    category = "persistence"
    next_action = "Verifique a integridade e as permissões do armazenamento."
    exit_code = 5


class QualityGateResultStorageReadError(QualityGateResultStorageError):
    code = "QUALITY_GATE_RESULT_STORAGE_READ_ERROR"


class QualityGateResultStorageWriteError(QualityGateResultStorageError):
    code = "QUALITY_GATE_RESULT_STORAGE_WRITE_ERROR"


class InvalidQualityGateResultStorageFormatError(QualityGateResultStorageError):
    code = "QUALITY_GATE_RESULT_STORAGE_INVALID"
    category = "validation"
    exit_code = 3


class DuplicateQualityGateResultError(QualityGateResultStorageError):
    code = "QUALITY_GATE_RESULT_DUPLICATE"
    category = "conflict"
    exit_code = 3


__all__ = [
    "DuplicateQualityGateResultError",
    "InvalidQualityGateResultStorageFormatError",
    "QualityGateResultStorageError",
    "QualityGateResultStorageReadError",
    "QualityGateResultStorageWriteError",
]
