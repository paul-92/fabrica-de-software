"""Erros específicos do contrato de Timeline."""

from asep.errors import AsepError


class DuplicateTimelineEventError(AsepError):
    code = "TIMELINE_EVENT_DUPLICATE"
    category = "conflict"
    next_action = "Gere um event_id único antes de repetir o registro."
    exit_code = 6
