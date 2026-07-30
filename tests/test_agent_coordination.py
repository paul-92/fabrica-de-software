from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from asep.agents import (
    AgentCapability,
    AgentError,
    AgentId,
    AgentMetadata,
)
from asep.agents.coordination import (
    AgentAssignment,
    AgentCoordinator,
    AgentExecutionQueue,
    AgentSelectionPolicy,
    AssignmentStatus,
    CapabilityResolutionError,
    CoordinationContext,
    CoordinationPolicy,
    CoordinationStatus,
    CoordinationValidationError,
    CoordinationValidator,
    InMemoryCoordinationMetrics,
    RegistryAgentCapabilityResolver,
)
from asep.agents.registry import InMemoryAgentRegistry
from asep.agents.runtime_models import (
    AgentExecutionResult,
    AgentExecutionStatus,
)
from asep.memory.models import (
    MemoryCategory,
    MemoryEntry,
    MemoryId,
)
from asep.planning import (
    ExecutionPlan,
    PlanningContext,
    PlanningEngine,
    PlanningRequest,
    PlanStep,
)
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEventType,
    TimelineRecorder,
)
from asep.workflow import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowExecutor,
    WorkflowValidator,
)

NOW = datetime(2026, 7, 30, 14, 0, tzinfo=UTC)


class RegisteredAgent:
    def __init__(self, agent_id: str, *capabilities: str) -> None:
        self.metadata = AgentMetadata(
            id=AgentId(value=agent_id),
            name=agent_id,
            description=f"Agent {agent_id}",
            version="1.0",
            capabilities=tuple(
                AgentCapability(id=item) for item in capabilities
            ),
        )

    def execute(self, request, context):  # pragma: no cover - Registry only
        raise AssertionError("Coordinator deve usar AgentRuntime.")


class FakeRuntime:
    def __init__(self, failed_steps=()) -> None:
        self.requests = []
        self.failed_steps = set(failed_steps)

    def execute(self, request):
        self.requests.append(request)
        failed = request.workflow_step_id in self.failed_steps
        return AgentExecutionResult(
            execution_id=request.execution_id,
            agent_id=request.agent_id,
            status=(
                AgentExecutionStatus.FAILED
                if failed
                else AgentExecutionStatus.SUCCEEDED
            ),
            started_at=NOW,
            completed_at=NOW,
            duration_seconds=0,
            attempts=1,
            error=(
                AgentError(code="failed", message="Expected failure.")
                if failed
                else None
            ),
            metadata=request.metadata,
        )


def registry() -> InMemoryAgentRegistry:
    result = InMemoryAgentRegistry()
    result.register(RegisteredAgent("analyst", "analysis"))
    result.register(RegisteredAgent("builder", "implementation"))
    result.register(RegisteredAgent("workflow-agent", "workflow_step"))
    return result


def plan() -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-1",
        goal="Deliver",
        steps=(
            PlanStep(
                step_id="analyze",
                description="Analyze",
                required_capability="analysis",
                priority=1,
            ),
            PlanStep(
                step_id="build",
                description="Build",
                required_capability="implementation",
                dependencies=("analyze",),
            ),
        ),
        estimated_cost=2,
        estimated_duration_seconds=120,
        created_at=NOW,
    )


def timeline():
    repository = InMemoryTimelineRepository()
    counter = 0

    def event_id():
        nonlocal counter
        counter += 1
        return f"event-{counter}"

    return repository, TimelineRecorder(
        repository, clock=lambda: NOW, id_generator=event_id
    )


def test_assignment_is_strict_immutable_and_typed() -> None:
    assignment = AgentAssignment(
        assignment_id="assignment",
        plan_step_id="step",
        agent_id=AgentId(value="agent"),
        required_capability="analysis",
        priority=0,
        created_at=NOW,
    )

    assert assignment.status is AssignmentStatus.PENDING
    with pytest.raises(ValidationError):
        assignment.status = AssignmentStatus.COMPLETED


def test_resolver_prefers_explicit_agent_then_affinity() -> None:
    available = registry()
    resolver = RegistryAgentCapabilityResolver(
        available,
        AgentSelectionPolicy(affinity={"analysis": "analyst"}),
    )

    assert resolver.resolve(plan().steps[0]) == AgentId(value="analyst")


def test_resolver_rejects_missing_capability() -> None:
    resolver = RegistryAgentCapabilityResolver(registry())
    step = PlanStep(
        step_id="unknown",
        description="Unknown",
        required_capability="missing",
    )

    with pytest.raises(CapabilityResolutionError):
        resolver.resolve(step)


def test_queue_obeys_dependencies_before_priority() -> None:
    execution_plan = plan()
    assignments = (
        AgentAssignment(
            assignment_id="build",
            plan_step_id="build",
            agent_id=AgentId(value="builder"),
            required_capability="implementation",
            priority=0,
            created_at=NOW,
        ),
        AgentAssignment(
            assignment_id="analyze",
            plan_step_id="analyze",
            agent_id=AgentId(value="analyst"),
            required_capability="analysis",
            priority=9,
            created_at=NOW,
        ),
    )

    ordered = AgentExecutionQueue().order(
        execution_plan, assignments, CoordinationPolicy()
    )

    assert tuple(item.plan_step_id for item in ordered) == (
        "analyze",
        "build",
    )


def test_validator_rejects_incomplete_assignments() -> None:
    context = CoordinationContext(execution_plan=plan())

    with pytest.raises(CoordinationValidationError):
        CoordinationValidator().validate_assignments(
            context, (), registry(), CoordinationPolicy()
        )


def test_coordinator_executes_sequentially_and_aggregates() -> None:
    repository, recorder = timeline()
    runtime = FakeRuntime()
    metrics = InMemoryCoordinationMetrics()
    coordinator = AgentCoordinator(
        registry(),
        runtime,
        timeline=recorder,
        metrics=metrics,
        clock=lambda: NOW,
        timer=iter((1.0, 1.5)).__next__,
    )

    result = coordinator.coordinate(
        CoordinationContext(
            execution_plan=plan(),
            metadata={"run_id": "run-1"},
        )
    )

    assert result.status is CoordinationStatus.COMPLETED
    assert [item.workflow_step_id for item in runtime.requests] == [
        "analyze",
        "build",
    ]
    assert all(
        item.status is AssignmentStatus.COMPLETED
        for item in result.assignments
    )
    assert metrics.snapshot().coordinated_plans_total == 1
    event_types = [
        event.type for event in repository.list_by_run("run-1")
    ]
    assert event_types[0] is TimelineEventType.COORDINATION_STARTED
    assert event_types[-1] is TimelineEventType.COORDINATION_COMPLETED
    assert event_types.count(TimelineEventType.AGENT_SELECTED) == 2


def test_coordinator_stops_and_marks_remaining_assignment_skipped() -> None:
    _, recorder = timeline()
    runtime = FakeRuntime(failed_steps={"analyze"})
    coordinator = AgentCoordinator(
        registry(), runtime, timeline=recorder, clock=lambda: NOW
    )

    result = coordinator.coordinate(
        CoordinationContext(
            execution_plan=plan(), metadata={"run_id": "run-failed"}
        )
    )

    assert result.status is CoordinationStatus.PARTIAL
    assert len(runtime.requests) == 1
    assert result.assignments[0].status is AssignmentStatus.FAILED
    assert result.assignments[1].status is AssignmentStatus.SKIPPED


def test_coordination_passes_memory_to_runtime_without_executing_tools() -> None:
    _, recorder = timeline()
    runtime = FakeRuntime()
    memory = MemoryEntry(
        memory_id=MemoryId(value="memory-1"),
        agent_id=AgentId(value="analyst"),
        execution_id="previous",
        category=MemoryCategory.DECISION,
        content="Use deterministic rules.",
        created_at=NOW,
        updated_at=NOW,
    )
    coordinator = AgentCoordinator(
        registry(), runtime, timeline=recorder, clock=lambda: NOW
    )

    coordinator.coordinate(
        CoordinationContext(
            execution_plan=plan(),
            memory=(memory,),
            metadata={"run_id": "run-memory"},
        )
    )

    assert runtime.requests[0].input["memory"][0]["content"] == (
        "Use deterministic rules."
    )


def test_coordination_failure_is_observed() -> None:
    repository, recorder = timeline()
    metrics = InMemoryCoordinationMetrics()
    coordinator = AgentCoordinator(
        registry(),
        FakeRuntime(),
        timeline=recorder,
        metrics=metrics,
    )
    invalid = ExecutionPlan(
        plan_id="empty",
        goal="Empty",
        steps=(),
        estimated_cost=0,
        estimated_duration_seconds=0,
        created_at=NOW,
    )

    with pytest.raises(CoordinationValidationError):
        coordinator.coordinate(
            CoordinationContext(
                execution_plan=invalid,
                metadata={"run_id": "run-invalid"},
            )
        )

    assert metrics.snapshot().coordination_failures == 1
    assert repository.list_by_run("run-invalid")[-1].type is (
        TimelineEventType.COORDINATION_FAILED
    )


@dataclass
class WorkflowStep:
    id: str

    def execute(self, context):
        assert context.values["coordination_result"]["status"] == "completed"


def test_workflow_integrates_planning_coordination_and_runtime() -> None:
    _, planning_recorder = timeline()
    _, coordination_recorder = timeline()
    _, workflow_recorder = timeline()
    coordinator = AgentCoordinator(
        registry(),
        FakeRuntime(),
        timeline=coordination_recorder,
        clock=lambda: NOW,
    )
    engine = WorkflowEngine(
        WorkflowValidator(),
        WorkflowExecutor(workflow_recorder, clock=lambda: NOW),
        planner=PlanningEngine(
            timeline=planning_recorder, clock=lambda: NOW
        ),
        coordinator=coordinator,
    )

    result = engine.execute(
        WorkflowDefinition(
            id="coordinated", steps=(WorkflowStep("first"),)
        ),
        WorkflowContext(run_id="run-workflow"),
    )

    assert result.context.values["coordination_result"]["plan_id"].startswith(
        "plan-"
    )


def test_planning_result_can_be_coordinated_directly() -> None:
    _, planning_recorder = timeline()
    _, coordination_recorder = timeline()
    planning_result = PlanningEngine(
        timeline=planning_recorder, clock=lambda: NOW
    ).plan(
        PlanningRequest(
            goal="Analyze",
            context=PlanningContext(
                objective="Analyze",
                workflow={
                    "steps": [
                        {
                            "id": "analysis",
                            "required_capability": "analysis",
                        }
                    ]
                },
                available_capabilities=("analysis",),
            ),
            workflow_execution_id="run-planning",
        )
    )

    result = AgentCoordinator(
        registry(),
        FakeRuntime(),
        timeline=coordination_recorder,
        clock=lambda: NOW,
    ).coordinate(
        CoordinationContext(
            execution_plan=planning_result.plan,
            metadata={"run_id": "run-planning"},
        )
    )

    assert result.status is CoordinationStatus.COMPLETED
