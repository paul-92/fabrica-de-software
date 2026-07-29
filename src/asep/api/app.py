"""Application factory da Dashboard API."""

from __future__ import annotations

from fastapi import FastAPI

from asep.application import RunQueryService
from asep.api.errors import register_exception_handlers
from asep.api.routes import (
    create_health_router,
    create_metrics_router,
    create_runs_router,
)
from asep.metrics import MetricsService


def create_app(
    run_query_service: RunQueryService,
    metrics_service: MetricsService,
) -> FastAPI:
    app = FastAPI(
        title="ASEP Dashboard API",
        description=(
            "Internal read-only API backed by non-durable in-memory "
            "repositories in the default composition."
        ),
        version="0.1.0",
    )
    app.state.run_query_service = run_query_service
    app.state.metrics_service = metrics_service
    register_exception_handlers(app)
    app.include_router(create_health_router())
    app.include_router(create_runs_router(run_query_service))
    app.include_router(create_metrics_router(metrics_service))
    return app
