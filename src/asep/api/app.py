"""Application factory da Dashboard API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from asep.application import (
    IntelligentEngineeringApplicationService,
    RunQueryService,
    ProjectService,
)
from asep.api.errors import register_exception_handlers
from asep.api.ai_runtime_routes import create_ai_runtime_router
from asep.application import AIRuntimeConnectionService
from asep.api.intelligent_engineering_routes import (
    create_intelligent_engineering_router,
)
from asep.api.project_routes import create_projects_router
from asep.api.routes import (
    create_health_router,
    create_metrics_router,
    create_runs_router,
)
from asep.metrics import MetricsService
from asep.configuration.models import DEFAULT_CORS_ORIGINS


def create_app(
    run_query_service: RunQueryService,
    metrics_service: MetricsService,
    intelligent_engineering_service: (
        IntelligentEngineeringApplicationService | None
    ) = None,
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS,
    project_service: ProjectService | None = None,
    ai_runtime_connection_service: AIRuntimeConnectionService | None = None,
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
    app.state.intelligent_engineering_service = (
        intelligent_engineering_service
    )
    app.state.cors_origins = cors_origins
    app.state.project_service = project_service
    app.state.ai_runtime_connection_service = ai_runtime_connection_service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    register_exception_handlers(app)
    app.include_router(create_health_router())
    app.include_router(create_runs_router(run_query_service))
    app.include_router(create_metrics_router(metrics_service))
    if project_service is not None:
        app.include_router(create_projects_router(project_service))
    if ai_runtime_connection_service is not None:
        app.include_router(
            create_ai_runtime_router(ai_runtime_connection_service)
        )
    if intelligent_engineering_service is not None:
        app.include_router(
            create_intelligent_engineering_router(
                intelligent_engineering_service
            )
        )
    return app
