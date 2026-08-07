"""Composition root da aplicação HTTP local."""

from __future__ import annotations

from fastapi import FastAPI
from pathlib import Path

from asep.ai_runtime import CodexAIRuntimeDiagnostics, CodexDiagnosticsConfig

from asep.api.app import create_app
from asep.application import (
    IntelligentEngineeringApplicationService,
    RunQueryService,
    ProjectService,
    AIRuntimeConnectionService,
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
from asep.repair import ControlledRepairExecutor
from asep.repositories import RepositoryBundle, RepositoryFactory
from asep.timeline import TimelineRecorder
from asep.tools import (
    InMemoryToolRegistry,
    RunTestsTool,
    ToolExecutionService,
    WriteFileTool,
)


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
    project_service = ProjectService(repositories.project_repository)
    ai_runtime_connection_service = AIRuntimeConnectionService(
        (
            CodexAIRuntimeDiagnostics(
                CodexDiagnosticsConfig(working_directory=Path.cwd())
            ),
        )
    )
    intelligent_engineering_service = _create_intelligent_engineering_service(
        settings,
        repositories,
    )
    return create_app(
        query_service,
        metrics_service,
        intelligent_engineering_service=intelligent_engineering_service,
        cors_origins=settings.cors_origins,
        project_service=project_service,
        ai_runtime_connection_service=ai_runtime_connection_service,
    )
