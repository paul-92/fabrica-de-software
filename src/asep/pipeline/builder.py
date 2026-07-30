"""Composition root do pipeline E2E."""

from __future__ import annotations

from collections.abc import Iterable

from asep.agents import (
    AgentExecutionPolicy,
    AgentExecutionService,
    InMemoryAgentExecutionMetrics,
    InMemoryAgentRegistry,
)
from asep.agents.coordination import (
    AgentCoordinator,
    InMemoryCoordinationMetrics,
)
from asep.agents.developer import DeveloperAgent
from asep.memory import (
    ContextBuilder,
    InMemoryMemoryMetrics,
    MemoryService,
)
from asep.configuration import ApplicationSettings
from asep.pipeline.engine import ASEPEngine
from asep.pipeline.pipeline import ExecutionPipeline, PipelineMetricSources
from asep.planning import InMemoryPlanningMetrics, PlanningEngine
from asep.repositories import RepositoryFactory
from asep.runtime.recovery import (
    DefaultExecutionSupervisor,
    ExecutionRecoveryService,
    InMemoryRecoveryMetrics,
    RecoveryPolicy,
)
from asep.timeline import (
    TimelineRecorder,
)
from asep.tools import (
    InMemoryToolMetrics,
    InMemoryToolRegistry,
    ListDirectoryTool,
    ReadDocumentationTool,
    ReadFileTool,
    SearchFilesTool,
    Tool,
    ToolExecutionPolicy,
    ToolExecutionService,
)
from asep.workflow import WorkflowEngine, WorkflowExecutor, WorkflowValidator
from asep.workflow.orchestrator import WorkflowOrchestrator


class PipelineBuilder:
    def __init__(
        self,
        *,
        tools: Iterable[Tool] | None = None,
        recovery_policy: RecoveryPolicy | None = None,
    ) -> None:
        self._tools = tuple(tools) if tools is not None else None
        self._recovery_policy = recovery_policy

    def build(self) -> ASEPEngine:
        repositories = RepositoryFactory(
            ApplicationSettings(storage_backend="memory")
        ).create()
        timeline_repository = repositories.timeline_repository
        timeline = TimelineRecorder(timeline_repository)

        tool_registry = InMemoryToolRegistry()
        tool_set = self._tools or (
            ListDirectoryTool(),
            SearchFilesTool(),
            ReadFileTool(),
            ReadDocumentationTool(),
        )
        for tool in tool_set:
            tool_registry.register(tool)
        tool_metrics = InMemoryToolMetrics()
        tool_execution = ToolExecutionService(
            tool_registry,
            timeline=timeline,
            metrics=tool_metrics,
            policy=ToolExecutionPolicy(fail_fast=False),
        )

        memory_metrics = InMemoryMemoryMetrics()
        memory = MemoryService(
            repositories.memory_store,
            timeline=timeline,
            metrics=memory_metrics,
        )
        context_builder = ContextBuilder(
            memory, timeline=timeline
        )

        agent_registry = InMemoryAgentRegistry()
        agent_registry.register(DeveloperAgent(tool_execution))
        agent_metrics = InMemoryAgentExecutionMetrics()
        runtime = AgentExecutionService(
            agent_registry,
            timeline=timeline,
            metrics=agent_metrics,
            policy=AgentExecutionPolicy(fail_fast=False),
            tool_executor=tool_execution,
            context_provider=context_builder,
        )

        recovery_metrics = InMemoryRecoveryMetrics()
        recovery = ExecutionRecoveryService(
            timeline=timeline,
            metrics=recovery_metrics,
            policy=self._recovery_policy,
        )
        supervisor = DefaultExecutionSupervisor(
            runtime,
            recovery,
            timeline=timeline,
            metrics=recovery_metrics,
        )

        coordination_metrics = InMemoryCoordinationMetrics()
        coordinator = AgentCoordinator(
            agent_registry,
            supervisor,
            timeline=timeline,
            metrics=coordination_metrics,
        )

        planning_metrics = InMemoryPlanningMetrics()
        planner = PlanningEngine(
            timeline=timeline,
            metrics=planning_metrics,
            memory=memory,
            tool_registry=tool_registry,
        )

        workflow_engine = WorkflowEngine(
            WorkflowValidator(),
            WorkflowExecutor(timeline),
        )
        workflow = WorkflowOrchestrator(
            repositories.run_repository,
            timeline_repository,
            engine=workflow_engine,
        )
        pipeline = ExecutionPipeline(
            workflow=workflow,
            planner=planner,
            coordinator=coordinator,
            tools=tool_registry,
            memory=memory,
            timeline=timeline_repository,
            metrics=PipelineMetricSources(
                planning=planning_metrics,
                coordination=coordination_metrics,
                recovery=recovery_metrics,
                agents=agent_metrics,
                tools=tool_metrics,
                memory=memory_metrics,
            ),
        )
        return ASEPEngine(pipeline)


__all__ = ["PipelineBuilder"]
