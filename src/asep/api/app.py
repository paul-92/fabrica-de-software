"""Application factory da Dashboard API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from asep.application import (
    AgentCatalogService,
    AgentRuntimeProjectionService,
    IntelligentEngineeringApplicationService,
    RunQueryService,
    ProjectService,
    ProjectAIRuntimeExecutionService,
    ProjectSessionService,
    ProjectSessionMemoryService,
    ProjectWorkspaceService,
    SequentialQualityGateQueryService,
)
from asep.api.errors import register_exception_handlers
from asep.api.agent_routes import (
    create_agent_catalog_router,
    create_agent_runtime_projection_router,
)
from asep.api.ai_runtime_routes import create_ai_runtime_router
from asep.application import AIRuntimeConnectionService
from asep.api.intelligent_engineering_routes import (
    create_intelligent_engineering_router,
)
from asep.api.project_routes import create_projects_router
from asep.api.sequential_quality_routes import create_sequential_quality_router
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
    project_ai_runtime_execution_service: ProjectAIRuntimeExecutionService | None = None,
    project_session_service: ProjectSessionService | None = None,
    project_session_memory_service: ProjectSessionMemoryService | None = None,
    project_workspace_service: ProjectWorkspaceService | None = None,
    agent_catalog_service: AgentCatalogService | None = None,
    agent_runtime_projection_service: AgentRuntimeProjectionService | None = None,
    sequential_quality_gate_service: SequentialQualityGateQueryService | None = None,
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
    app.state.project_session_service = project_session_service
    app.state.agent_catalog_service = agent_catalog_service
    app.state.agent_runtime_projection_service = agent_runtime_projection_service
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
    if agent_catalog_service is not None:
        app.include_router(create_agent_catalog_router(agent_catalog_service))
    if agent_runtime_projection_service is not None:
        app.include_router(
            create_agent_runtime_projection_router(
                agent_runtime_projection_service
            )
        )
    if sequential_quality_gate_service is not None:
        app.include_router(
            create_sequential_quality_router(sequential_quality_gate_service)
        )
    if project_service is not None:
        app.include_router(
            create_projects_router(
                project_service,
                project_ai_runtime_execution_service,
                project_session_service,
                project_session_memory_service,
                project_workspace_service,
            )
        )
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
