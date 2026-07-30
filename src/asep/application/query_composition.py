"""Composição local das consultas de histórico."""

from __future__ import annotations

from asep.application.run_query import RunQueryService
from asep.configuration import Configuration
from asep.repositories import RepositoryFactory

_repositories = RepositoryFactory(Configuration.load()).create()
_run_query_service = RunQueryService(
    _repositories.run_repository,
    _repositories.timeline_repository,
)


def get_run_query_service() -> RunQueryService:
    """Retorna o serviço compartilhado durante a vida do processo atual."""
    return _run_query_service
