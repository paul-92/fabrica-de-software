"""Composição local das consultas de histórico."""

from __future__ import annotations

from asep.application.run_query import RunQueryService
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository

_run_repository = InMemoryRunRepository()
_timeline_repository = InMemoryTimelineRepository()
_run_query_service = RunQueryService(
    _run_repository,
    _timeline_repository,
)


def get_run_query_service() -> RunQueryService:
    """Retorna o serviço compartilhado durante a vida do processo atual."""
    return _run_query_service
