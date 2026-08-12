"""Composition root da aplicação HTTP local."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fastapi import FastAPI
from pathlib import Path

from asep.ai_runtime import (
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
    create_intelligent_engineering_application_service,
)
from asep.ai_planning import (
    AutonomousEngineeringService,
    DeterministicReflectionEvaluator,
    DeterministicRepairPlanGenerator,
    DeterministicRepairProposalPlanner,
)
from asep.configuration import ApplicationSettings, Configuration
from asep.metrics import MetricsService
from asep.intelligence import (
    KnowledgeAwarePlanningAdapter,
    ToolAwarePlanningAdapter,
)
from asep.planning import PlanningEngine
from asep.pipeline import ASEPEngine, PipelineBuilder
from asep.orchestrator import (
    Orchestrator,
    create_sequential_operational_composition,
)
from asep.repair import ControlledRepairExecutor
from asep.repositories import RepositoryBundle, RepositoryFactory
from asep.timeline import TimelineRecorder
from asep.tools import (
    InMemoryToolRegistry,
    RunTestsTool,
    ToolExecutionService,
    WriteFileTool,
)
from asep.registry.agent_catalog_source import DeclarativeAgentCatalogSource


@dataclass(frozen=True, slots=True)
class OperationalComposition:
    app: FastAPI
    engine: ASEPEngine


@dataclass(frozen=True, slots=True)
class SequentialOperationalApiComposition:
    app: FastAPI
    orchestrator: Orchestrator


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


def _create_configured_app(
    settings: ApplicationSettings,
    *,
    agent_runtime_projection_service: AgentRuntimeProjectionService | None = None,
    sequential_quality_gate_service: SequentialQualityGateQueryService | None = None,
) -> FastAPI:
    repositories = RepositoryFactory(settings).create()
    query_service = RunQueryService(
        repositories.run_repository,
        repositories.timeline_repository,
    )
    metrics_service = MetricsService(query_service)
    agent_catalog_service = AgentCatalogService(
        DeclarativeAgentCatalogSource(settings.agent_catalog_directory)
    )
    project_service = ProjectService(repositories.project_repository)
    ai_runtime_connection_service = AIRuntimeConnectionService(
        (
            CodexAIRuntimeDiagnostics(
                CodexDiagnosticsConfig(working_directory=Path.cwd())
            ),
        )
    )
    runtime_registry = InMemoryAIRuntimeRegistry()
    runtime_registry.register(
        CodexAIRuntime(CodexAIRuntimeConfig(workspace=Path.cwd()))
    )
    project_session_service = ProjectSessionService(
        project_service,
        repositories.project_session_repository,
        repositories.project_execution_repository,
    )
    project_memory_service = ProjectSessionMemoryService(
        project_service,
        project_session_service,
        repositories.session_memory_repository,
    )
    session_memory_search_service = SessionMemorySearchService(
        project_session_service,
        repositories.session_memory_query_source,
    )
    project_workspace_service = ProjectWorkspaceService(project_service)
    project_runtime_execution = ProjectAIRuntimeExecutionService(
        project_service,
        runtime_registry,
        project_session_service,
        repositories.project_execution_repository,
        memory_service=project_memory_service,
    )
    intelligent_engineering_service = _create_intelligent_engineering_service(
        settings,
        repositories,
    )
    branding_query_service = BrandingQueryService(
        repositories.branding_repository,
    )
    return create_app(
        query_service,
        metrics_service,
        intelligent_engineering_service=intelligent_engineering_service,
        cors_origins=settings.cors_origins,
        project_service=project_service,
        ai_runtime_connection_service=ai_runtime_connection_service,
        project_ai_runtime_execution_service=project_runtime_execution,
        project_session_service=project_session_service,
        project_session_memory_service=project_memory_service,
        project_workspace_service=project_workspace_service,
        agent_catalog_service=agent_catalog_service,
        agent_runtime_projection_service=agent_runtime_projection_service,
        sequential_quality_gate_service=sequential_quality_gate_service,
        session_memory_search_service=session_memory_search_service,
        branding_query_service=branding_query_service,
    )


def create_default_app(
    repository_settings: ApplicationSettings | None = None,
) -> FastAPI:
    settings = repository_settings or Configuration.load()
    return _create_configured_app(settings)


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
    "SequentialOperationalApiComposition",
    "create_default_app",
    "create_default_operational_composition",
    "create_sequential_operational_api_composition",
]
