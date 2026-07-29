"""Composition root da aplicação HTTP local."""

from __future__ import annotations

from fastapi import FastAPI

from asep.api.app import create_app
from asep.application import RunQueryService
from asep.metrics import MetricsService
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository


def create_default_app() -> FastAPI:
    run_repository = InMemoryRunRepository()
    timeline_repository = InMemoryTimelineRepository()
    query_service = RunQueryService(
        run_repository,
        timeline_repository,
    )
    metrics_service = MetricsService(query_service)
    return create_app(query_service, metrics_service)
