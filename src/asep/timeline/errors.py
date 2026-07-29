"""Erros específicos do contrato de Timeline."""

from asep.errors import AsepError


class DuplicateTimelineEventError(AsepError):
    code = "TIMELINE_EVENT_DUPLICATE"
    category = "conflict"
    next_action = "Gere um event_id único antes de repetir o registro."
    exit_code = 6


class TimelineStorageError(AsepError):
    code = "TIMELINE_STORAGE_ERROR"
    category = "persistence"
    next_action = "Verifique integridade e permissões do arquivo de Timeline."
    exit_code = 5


class TimelineStorageReadError(TimelineStorageError):
    code = "TIMELINE_STORAGE_READ_ERROR"


class TimelineStorageWriteError(TimelineStorageError):
    code = "TIMELINE_STORAGE_WRITE_ERROR"


class InvalidTimelineStorageFormatError(TimelineStorageError):
    code = "TIMELINE_STORAGE_INVALID"
    category = "validation"
    next_action = (
        "Restaure um arquivo de Timeline válido; não sobrescreva a "
        "evidência corrompida."
    )
    exit_code = 3
