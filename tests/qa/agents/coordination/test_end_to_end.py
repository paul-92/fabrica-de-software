"""Integração end-to-end entre Coordination e Agent Runtime."""

from __future__ import annotations

from datetime import UTC, datetime

from asep.agents import (
    AgentCapability,
    AgentExecutionService,
    AgentId,
    AgentMetadata,
    AgentStatus,
    InMemoryAgentRegistry,
)
from asep.agents.coordination import (
    AgentCoordinator,
    AgentCoordinatorAdapter,
    AssignmentStatus,
    CoordinationStatus,
)
from asep.execution.models import AgentContext, AgentResult
from asep.planning import (
    ExecutionPlan,
    PlanningResult,
    PlanningStatistics,
    PlanStep,
)
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEventType,
    TimelineRecorder,
)

NOW = datetime(2026, 7, 31, 16, 30, tzinfo=UTC)


class ImplementationAgent:
    """Agente fake executado pelo runtime real da ASEP."""

    def __init__(self) -> None:
        self._metadata = AgentMetadata(
            id=AgentId(value="developer"),
            name="Developer",
            description="Agente determinístico de implementação.",
            version="1.0",
            capabilities=(
                AgentCapability(id="implement_requirement"),
            ),
        )
        self.contexts: list[AgentContext] = []

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def execute(
        self,
        request,
        context: AgentContext,
    ) -> AgentResult:
        del request
        self.contexts.append(context)

        return AgentResult(
            status=AgentStatus.COMPLETED,
            agent_id=self.metadata.id.value,
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=context.started_at,
            finished_at=NOW,
            messages=["Requisito implementado."],
        )


def timeline() -> tuple[
    InMemoryTimelineRepository,
    TimelineRecorder,
]:
    repository = InMemoryTimelineRepository()
    counter = 0

    def event_id() -> str:
        nonlocal counter
        counter += 1
        return f"event-{counter}"

    recorder = TimelineRecorder(
        repository,
        clock=lambda: NOW,
        id_generator=event_id,
    )

    return repository, recorder


def planning_result() -> PlanningResult:
    plan = ExecutionPlan(
        plan_id="plan-runtime-e2e",
        goal="Implementar cadastro de clientes.",
        steps=(
            PlanStep(
                step_id="REQ-001",
                description="Implementar cadastro de clientes",
                required_capability="implement_requirement",
            ),
        ),
        estimated_cost=1,
        estimated_duration_seconds=60,
        created_at=NOW,
    )

    return PlanningResult(
        plan=plan,
        warnings=(),
        validation_messages=("Plano validado.",),
        statistics=PlanningStatistics(
            total_steps=1,
            dependency_count=0,
            maximum_depth=1,
            estimated_cost=1,
            estimated_duration_seconds=60,
            memory_entries_considered=0,
        ),
    )


def test_coordination_executes_agent_through_real_runtime() -> None:
    agent = ImplementationAgent()
    registry = InMemoryAgentRegistry()
    registry.register(agent)

    timeline_repository, timeline_recorder = timeline()

    runtime = AgentExecutionService(
        registry,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    coordinator = AgentCoordinator(
        registry,
        runtime,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    adapter = AgentCoordinatorAdapter(
        coordinator=coordinator,
    )

    result = adapter.coordinate(planning_result())

    assert result.status is CoordinationStatus.COMPLETED
    assert result.plan_id == "plan-runtime-e2e"
    assert len(result.assignments) == 1
    assert result.assignments[0].status is AssignmentStatus.COMPLETED
    assert result.assignments[0].agent_id == AgentId(value="developer")

    assert len(result.results) == 1
    assert result.results[0].agent_result is not None
    assert result.results[0].agent_result.messages == [
        "Requisito implementado."
    ]

    assert len(agent.contexts) == 1
    assert agent.contexts[0].run_id == "plan-runtime-e2e"
    assert agent.contexts[0].stage_id == "REQ-001"
    assert agent.contexts[0].objective == (
        "Implementar cadastro de clientes"
    )

    event_types = tuple(
        event.type
        for event in timeline_repository.list_by_run(
            "plan-runtime-e2e"
        )
    )

    assert TimelineEventType.COORDINATION_STARTED in event_types
    assert TimelineEventType.AGENT_EXECUTION_REQUESTED in event_types
    assert TimelineEventType.AGENT_EXECUTION_SUCCEEDED in event_types
    assert TimelineEventType.COORDINATION_COMPLETED in event_types