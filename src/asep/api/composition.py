"""Composition root da aplicação HTTP local."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fastapi import FastAPI
from pathlib import Path

from asep.ai_runtime import (
    AIRuntimeRegistry,
    CodexAIRuntime,
    CodexAIRuntimeConfig,
    CodexAIRuntimeDiagnostics,
    CodexDiagnosticsConfig,
    InMemoryAIRuntimeRegistry,
)

from asep.api.app import create_app
from asep.application import (
    AgentCatalogService,
    AgentRuntimeProjectionService,
    IntelligentEngineeringApplicationService,
    RunQueryService,
    ProjectService,
    AIRuntimeConnectionService,
    ProjectAIRuntimeExecutionService,
    ProjectSessionService,
    ProjectSessionMemoryService,
    ProjectWorkspaceService,
    AuthorizedSequentialProject,
    SequentialProjectResolver,
    SequentialQualityGateQueryService,
    SessionMemorySearchService,
    BrandingQueryService,
    BrandingAdministrationService,
    DeterministicEngineeringTaskDecomposer,
    EngineeringTaskDecomposer,
    EngineeringImplementationProvider,
    AIBackedEngineeringImplementationProvider,
    MeteredEngineeringImplementationProvider,
    ProjectEngineeringAgentExecutor,
    ProjectEngineeringExecutionService,
    ProjectEngineeringPlanningService,
    ProjectQualityGateService,
    ProjectRepairService,
    ProjectValidationService,
    create_intelligent_engineering_application_service,
)
from asep.ai_planning import (
    AutonomousEngineeringService,
    DeterministicReflectionEvaluator,
    DeterministicRepairPlanGenerator,
    DeterministicRepairProposalPlanner,
)
from asep.agents import (
    AgentExecutionPolicy,
    AgentExecutionService,
    InMemoryAgentRegistry,
)
from asep.agents.developer import DeveloperAgent
from asep.configuration import ApplicationSettings, Configuration
from asep.metrics import MetricsService
from asep.intelligence import (
    KnowledgeAwarePlanningAdapter,
    ToolAwarePlanningAdapter,
)
from asep.planning import PlanningEngine
from asep.project_analysis import ProjectAnalyzer
from asep.pipeline import ASEPEngine, PipelineBuilder
from asep.orchestrator import (
    Orchestrator,
    create_sequential_operational_composition,
)
from asep.quality.engine import QualityGateEngine
from asep.quality_results import QualityGateResultRepository
from asep.repair import (
    ControlledRepairExecutor,
    DeterministicRepairPlanner,
    PytestFailureAnalyzer,
    RepairPlanner,
)
from asep.repositories import RepositoryBundle, RepositoryFactory
from asep.timeline import TimelineRecorder
from asep.tools import (
    InMemoryToolRegistry,
    RunTestsTool,
    CompileAllTool,
    ToolExecutionPolicy,
    ToolExecutionService,
    WriteFileTool,
    node_validation_tools,
)
from asep.registry.agent_catalog_source import DeclarativeAgentCatalogSource
from asep.access import AccessService
from asep.access.models import (
    LEGACY_ADMIN_USER_ID, LEGACY_ORGANIZATION_ID, Membership, Organization,
    OrganizationRole, User, UserStatus,
)
from asep.projects import HostedWorkspaceManager
from asep.ai_usage import AIUsageService
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class OperationalComposition:
    app: FastAPI
    engine: ASEPEngine


@dataclass(frozen=True, slots=True)
class SequentialOperationalApiComposition:
    app: FastAPI
    orchestrator: Orchestrator


@dataclass(frozen=True, slots=True)
class TrustedBrandingAdministrationComposition:
    app: FastAPI
    branding_administration: BrandingAdministrationService


@dataclass(frozen=True, slots=True)
class ProjectEngineeringOperationalComposition:
    app: FastAPI
    project_engineering_execution: ProjectEngineeringExecutionService
    quality_gate_results: QualityGateResultRepository


@dataclass(frozen=True, slots=True)
class _ProjectApplicationServices:
    projects: ProjectService
    runtime_connection: AIRuntimeConnectionService
    runtime_execution: ProjectAIRuntimeExecutionService
    engineering_execution: ProjectEngineeringExecutionService | None
    sessions: ProjectSessionService
    memory: ProjectSessionMemoryService
    memory_search: SessionMemorySearchService
    workspace: ProjectWorkspaceService
    usage: AIUsageService


def _create_intelligent_engineering_service(
    settings: ApplicationSettings,
    repositories: RepositoryBundle,
) -> IntelligentEngineeringApplicationService | None:
    if settings.repair_workspace is None:
        return None

    timeline = TimelineRecorder(repositories.timeline_repository)
    operational_tools = (WriteFileTool(), RunTestsTool())
    tools = InMemoryToolRegistry()
    for tool in operational_tools:
        tools.register(tool)
    tool_execution = ToolExecutionService(tools, timeline=timeline)
    planner = PlanningEngine(timeline=timeline, tool_registry=tools)
    engineering = AutonomousEngineeringService(
        DeterministicRepairProposalPlanner(),
        DeterministicRepairPlanGenerator(),
        ControlledRepairExecutor(tool_execution, settings.repair_workspace),
        DeterministicReflectionEvaluator(),
    )
    return create_intelligent_engineering_application_service(
        planner,
        engineering,
        ToolAwarePlanningAdapter(
            KnowledgeAwarePlanningAdapter(),
            operational_tools,
        ),
    )


def _create_project_application_services(
    repositories: RepositoryBundle,
    *,
    settings: ApplicationSettings | None = None,
    runtime_registry: AIRuntimeRegistry | None = None,
    include_engineering_execution: bool = False,
    engineering_decomposer: EngineeringTaskDecomposer | None = None,
    implementation_provider: EngineeringImplementationProvider | None = None,
    repair_planner: RepairPlanner | None = None,
) -> _ProjectApplicationServices:
    effective_settings = settings or ApplicationSettings()
    project_service = ProjectService(
        repositories.project_repository,
        hosted_workspaces=HostedWorkspaceManager(effective_settings.hosted_root),
    )
    runtime_connection = AIRuntimeConnectionService(
        (
            CodexAIRuntimeDiagnostics(
                CodexDiagnosticsConfig(working_directory=Path.cwd())
            ),
        )
    )
    registry = runtime_registry or InMemoryAIRuntimeRegistry()
    if runtime_registry is None:
        registry.register(
            CodexAIRuntime(CodexAIRuntimeConfig(workspace=Path.cwd()))
        )
    sessions = ProjectSessionService(
        project_service,
        repositories.project_session_repository,
        repositories.project_execution_repository,
    )
    memory = ProjectSessionMemoryService(
        project_service,
        sessions,
        repositories.session_memory_repository,
    )
    usage = AIUsageService(repositories.ai_usage_repository)
    runtime_execution = ProjectAIRuntimeExecutionService(
        project_service,
        registry,
        sessions,
        repositories.project_execution_repository,
        memory_service=memory,
    ).with_usage_metering(usage)
    internal_execution = None
    engineering_tools = None
    if include_engineering_execution:
        tools_registry = InMemoryToolRegistry()
        for tool in (
            WriteFileTool(), RunTestsTool(), CompileAllTool(),
            *node_validation_tools(),
        ):
            tools_registry.register(tool)
        engineering_tools = ToolExecutionService(
            tools_registry,
            timeline=TimelineRecorder(repositories.timeline_repository),
            policy=ToolExecutionPolicy(fail_fast=False),
        )
        if implementation_provider is not None:
            agent_registry = InMemoryAgentRegistry()
            agent_registry.register(DeveloperAgent(engineering_tools))
            agent_execution = AgentExecutionService(
                agent_registry,
                timeline=TimelineRecorder(repositories.timeline_repository),
                policy=AgentExecutionPolicy(fail_fast=False),
            )
            effective_provider = (
                MeteredEngineeringImplementationProvider(implementation_provider, usage)
                if isinstance(implementation_provider, AIBackedEngineeringImplementationProvider)
                else implementation_provider
            )
            internal_execution = ProjectEngineeringAgentExecutor(
                agent_execution,
                effective_provider,
            )
    engineering_runtime_execution = ProjectAIRuntimeExecutionService(
        project_service,
        registry,
        sessions,
        repositories.project_execution_repository,
        memory_service=memory,
        engineering_planning=(
            ProjectEngineeringPlanningService(
                ProjectAnalyzer(),
                engineering_decomposer
                or DeterministicEngineeringTaskDecomposer(),
            )
            if include_engineering_execution
            else None
        ),
        internal_execution=internal_execution,
        defer_completion=include_engineering_execution,
    ).with_usage_metering(usage)
    engineering_execution = None
    if include_engineering_execution:
        assert engineering_tools is not None
        engineering_execution = ProjectEngineeringExecutionService(
            engineering_runtime_execution,
            project_service,
            repositories.project_execution_repository,
            memory,
            ProjectValidationService(engineering_tools),
            ProjectRepairService(
                PytestFailureAnalyzer(),
                repair_planner or DeterministicRepairPlanner(),
                engineering_tools,
            ),
            ProjectQualityGateService(
                QualityGateEngine(),
                repositories.quality_gate_result_repository,
            ),
        )
    return _ProjectApplicationServices(
        projects=project_service,
        runtime_connection=runtime_connection,
        runtime_execution=runtime_execution,
        engineering_execution=engineering_execution,
        sessions=sessions,
        memory=memory,
        memory_search=SessionMemorySearchService(
            sessions,
            repositories.session_memory_query_source,
        ),
        workspace=ProjectWorkspaceService(project_service), usage=usage,
    )


def _create_configured_app(
    settings: ApplicationSettings,
    *,
    agent_runtime_projection_service: AgentRuntimeProjectionService | None = None,
    sequential_quality_gate_service: SequentialQualityGateQueryService | None = None,
    repositories: RepositoryBundle | None = None,
    project_services: _ProjectApplicationServices | None = None,
) -> FastAPI:
    repositories = repositories or RepositoryFactory(settings).create()
    query_service = RunQueryService(
        repositories.run_repository,
        repositories.timeline_repository,
    )
    metrics_service = MetricsService(query_service)
    agent_catalog_service = AgentCatalogService(
        DeclarativeAgentCatalogSource(settings.agent_catalog_directory)
    )
    project_services = project_services or _create_project_application_services(
        repositories, settings=settings
    )
    intelligent_engineering_service = _create_intelligent_engineering_service(
        settings,
        repositories,
    )
    branding_query_service = BrandingQueryService(
        repositories.branding_repository,
    )
    access_service = _bootstrap_access(settings, repositories)
    return create_app(
        query_service,
        metrics_service,
        intelligent_engineering_service=intelligent_engineering_service,
        cors_origins=settings.cors_origins,
        project_service=project_services.projects,
        ai_runtime_connection_service=project_services.runtime_connection,
        project_ai_runtime_execution_service=project_services.runtime_execution,
        project_engineering_execution_service=(
            project_services.engineering_execution
        ),
        project_session_service=project_services.sessions,
        project_session_memory_service=project_services.memory,
        project_workspace_service=project_services.workspace,
        agent_catalog_service=agent_catalog_service,
        agent_runtime_projection_service=agent_runtime_projection_service,
        sequential_quality_gate_service=sequential_quality_gate_service,
        session_memory_search_service=project_services.memory_search,
        branding_query_service=branding_query_service,
        access_service=access_service,
        access_cookie_secure=settings.access_cookie_secure,
        ai_usage_service=project_services.usage,
    )


def _bootstrap_access(settings: ApplicationSettings, repositories: RepositoryBundle) -> AccessService:
    repository = repositories.access_repository
    now = datetime.now(UTC)
    repository.save_organization(Organization(
        organization_id=LEGACY_ORGANIZATION_ID, name="Legacy local", created_at=now,
    ))
    found = repository.get_user_by_email(settings.legacy_admin_email.strip().casefold())
    if found is None:
        user = User(user_id=LEGACY_ADMIN_USER_ID, email=settings.legacy_admin_email,
                    status=UserStatus.ACTIVE, created_at=now, updated_at=now)
        repository.save_user(user, AccessService.password_hash(settings.legacy_admin_password))
        repository.save_membership(Membership(
            organization_id=LEGACY_ORGANIZATION_ID, user_id=user.user_id,
            role=OrganizationRole.ADMIN, created_at=now,
        ))
    return AccessService(repository)


def create_default_app(
    repository_settings: ApplicationSettings | None = None,
) -> FastAPI:
    settings = repository_settings or Configuration.load()
    return _create_configured_app(settings)


def create_trusted_branding_administration_composition(
    repository_settings: ApplicationSettings | None = None,
) -> TrustedBrandingAdministrationComposition:
    settings = repository_settings or Configuration.load()
    repositories = RepositoryFactory(settings).create()
    administration = BrandingAdministrationService(
        repositories.branding_repository
    )
    return TrustedBrandingAdministrationComposition(
        app=_create_configured_app(settings, repositories=repositories),
        branding_administration=administration,
    )


def create_default_operational_composition(
    repository_settings: ApplicationSettings | None = None,
) -> OperationalComposition:
    settings = repository_settings or Configuration.load()
    pipeline = PipelineBuilder().build_composition()
    projection = AgentRuntimeProjectionService(
        pipeline.agent_registry,
        pipeline.agent_metrics,
    )
    return OperationalComposition(
        app=_create_configured_app(
            settings,
            agent_runtime_projection_service=projection,
        ),
        engine=pipeline.engine,
    )


def create_project_engineering_operational_composition(
    repository_settings: ApplicationSettings | None = None,
    *,
    runtime_registry: AIRuntimeRegistry | None = None,
    engineering_decomposer: EngineeringTaskDecomposer | None = None,
    implementation_provider: EngineeringImplementationProvider | None = None,
    repair_planner: RepairPlanner | None = None,
) -> ProjectEngineeringOperationalComposition:
    settings = repository_settings or Configuration.load()
    repositories = RepositoryFactory(settings).create()
    project_services = _create_project_application_services(
        repositories,
        settings=settings,
        runtime_registry=runtime_registry,
        include_engineering_execution=True,
        engineering_decomposer=engineering_decomposer,
        implementation_provider=implementation_provider,
        repair_planner=repair_planner,
    )
    engineering = project_services.engineering_execution
    if engineering is None:  # pragma: no cover - composition invariant
        raise RuntimeError("project engineering service was not composed")
    return ProjectEngineeringOperationalComposition(
        app=_create_configured_app(
            settings,
            repositories=repositories,
            project_services=project_services,
        ),
        project_engineering_execution=engineering,
        quality_gate_results=repositories.quality_gate_result_repository,
    )


def create_sequential_operational_api_composition(
    repository_settings: ApplicationSettings | None = None,
    *,
    authorized_projects: Iterable[AuthorizedSequentialProject] = (),
    authorized_roots: Iterable[Path] = (),
    project_resolver: SequentialProjectResolver | None = None,
) -> SequentialOperationalApiComposition:
    settings = repository_settings or Configuration.load()
    sequential = create_sequential_operational_composition(
        settings,
        authorized_projects=authorized_projects,
        authorized_roots=authorized_roots,
        project_resolver=project_resolver,
    )
    return SequentialOperationalApiComposition(
        app=_create_configured_app(
            settings,
            sequential_quality_gate_service=sequential.quality_gate_query,
        ),
        orchestrator=sequential.orchestrator,
    )


__all__ = [
    "OperationalComposition",
    "ProjectEngineeringOperationalComposition",
    "SequentialOperationalApiComposition",
    "TrustedBrandingAdministrationComposition",
    "create_default_app",
    "create_default_operational_composition",
    "create_project_engineering_operational_composition",
    "create_trusted_branding_administration_composition",
    "create_sequential_operational_api_composition",
]
