"""Erros da infraestrutura persistente de Runs."""

from asep.errors import AsepError


class RunStorageError(AsepError):
    code = "RUN_STORAGE_ERROR"
    category = "persistence"
    next_action = "Verifique integridade e permissões do arquivo de Runs."
    exit_code = 5


class RunStorageReadError(RunStorageError):
    code = "RUN_STORAGE_READ_ERROR"


class RunStorageWriteError(RunStorageError):
    code = "RUN_STORAGE_WRITE_ERROR"


class InvalidRunStorageFormatError(RunStorageError):
    code = "RUN_STORAGE_INVALID"
    category = "validation"
    next_action = (
        "Restaure um arquivo de Runs válido; não sobrescreva a "
        "evidência corrompida."
    )
    exit_code = 3
