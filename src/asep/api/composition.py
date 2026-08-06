"""Composition root da aplicação HTTP local."""

from __future__ import annotations

from fastapi import FastAPI

from asep.api.app import create_app
from asep.application import RunQueryService
from asep.configuration import ApplicationSettings, Configuration
from asep.metrics import MetricsService
from asep.repositories import RepositoryFactory


def create_default_app(
    repository_settings: ApplicationSettings | None = None,
) -> FastAPI:
    settings = repository_settings or Configuration.load()
    repositories = RepositoryFactory(settings).create()
    query_service = RunQueryService(
        repositories.run_repository,
        repositories.timeline_repository,
    )
    metrics_service = MetricsService(query_service)
    return create_app(
        query_service,
        metrics_service,
        cors_origins=settings.cors_origins,
    )
