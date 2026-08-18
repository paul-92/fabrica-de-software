"""Application factory da Dashboard API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from collections.abc import Callable

from asep.application import (
    AgentCatalogService,
    AgentRuntimeProjectionService,
    IntelligentEngineeringApplicationService,
    RunQueryService,
    ProjectService,
    ProjectAIRuntimeExecutionService,
    ProjectEngineeringExecutionService,
    ProjectSessionService,
    ProjectSessionMemoryService,
    ProjectWorkspaceService,
    SequentialQualityGateQueryService,
    SessionMemorySearchService,
    BrandingQueryService,
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
from asep.api.branding_routes import create_branding_router
from asep.api.routes import (
    create_health_router,
    create_metrics_router,
    create_runs_router,
)
from asep.metrics import MetricsService
from asep.configuration.models import DEFAULT_CORS_ORIGINS
from asep.access import AccessDeniedError, AccessService
from asep.api.access_routes import create_access_router
from asep.ai_usage import AIUsageService
from asep.api.ai_usage_routes import create_ai_usage_router
from asep.ai_quotas import AIQuotaService
from asep.api.ai_quota_routes import create_ai_quota_router
from asep.maintenance import MaintenanceActiveError, MaintenanceGate
from asep.project_lifecycle import InMemoryProjectLifecycleRepository
from asep.dependency_provisioning import SQLiteDependencyRequestRepository, SQLiteProvisioningEvidenceRepository


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
    session_memory_search_service: SessionMemorySearchService | None = None,
    branding_query_service: BrandingQueryService | None = None,
    project_engineering_execution_service: ProjectEngineeringExecutionService | None = None,
    access_service: AccessService | None = None,
    access_cookie_secure: bool = False,
    ai_usage_service: AIUsageService | None = None,
    ai_quota_service: AIQuotaService | None = None,
    readiness: Callable[[], bool] | None = None,
    maintenance_gate: MaintenanceGate | None = None,
    project_lifecycle_repository: InMemoryProjectLifecycleRepository | None = None,
    dependency_request_repository: SQLiteDependencyRequestRepository | None = None,
    provisioning_evidence_repository: SQLiteProvisioningEvidenceRepository | None = None,
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
    if maintenance_gate is not None:
        @app.middleware("http")
        async def block_mutations_during_maintenance(request, call_next):
            lease = None
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                try:
                    lease = maintenance_gate.begin_mutation()
                except MaintenanceActiveError:
                    return JSONResponse(status_code=503, content={"error": {"code": "MAINTENANCE", "message": "Service temporarily unavailable."}})
            try:
                return await call_next(request)
            finally:
                if lease is not None:
                    lease.release()
    if access_service is not None:
        @app.middleware("http")
        async def require_private_access(request, call_next):
            public = {"/api/v1/health", "/api/v1/ready", "/api/v1/access/login", "/api/v1/access/logout"}
            if request.method != "OPTIONS" and request.url.path.startswith("/api/v1/") and request.url.path not in public:
                try:
                    access_service.authenticate(request.cookies.get("asep_session"))
                except AccessDeniedError:
                    return JSONResponse(status_code=401, content={"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Authentication required."}})
            return await call_next(request)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    register_exception_handlers(app)
    app.include_router(create_health_router(readiness))
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
    principal_dependency = None
    if access_service is not None:
        access_router, principal_dependency = create_access_router(access_service, secure_cookie=access_cookie_secure)
        app.include_router(access_router)
    if project_service is not None:
        app.include_router(
            create_projects_router(
                project_service,
                project_ai_runtime_execution_service,
                project_session_service,
                project_session_memory_service,
                project_workspace_service,
                session_memory_search_service,
                project_engineering_execution_service,
                principal_dependency,
                project_lifecycle_repository,
                dependency_request_repository,
                provisioning_evidence_repository,
            )
        )
        if ai_usage_service is not None and principal_dependency is not None:
            app.include_router(create_ai_usage_router(ai_usage_service, project_service, principal_dependency))
        if ai_quota_service is not None and principal_dependency is not None:
            app.include_router(create_ai_quota_router(ai_quota_service, principal_dependency))
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
    if branding_query_service is not None:
        app.include_router(create_branding_router(branding_query_service))
    return app
