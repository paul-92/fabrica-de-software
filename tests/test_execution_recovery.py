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
from asep.agents.coordination import AgentCoordinator, CoordinationContext
from asep.agents.registry import InMemoryAgentRegistry
from asep.agents.runtime_models import (
    AgentExecutionRequest,
    AgentExecutionResult,
    AgentExecutionStatus,
)
from asep.planning import (
    ExecutionPlan,
    PlanningEngine,
    PlanStep,
)
from asep.runtime.recovery import (
    BackoffKind,
    ConstantBackoff,
    DefaultExecutionSupervisor,
    ExecutionRecoveryService,
    ExecutionStateMachine,
    ExponentialBackoff,
    FailureCategory,
    FailureClassificationError,
    FailureClassifier,
    FallbackAction,
    FallbackPolicy,
    InMemoryRecoveryMetrics,
    InvalidStateTransitionError,
    LinearBackoff,
    RecoveryContext,
    RecoveryPolicy,
    RecoveryPolicyError,
    RecoveryValidator,
    RetryDecision,
    RetryPolicy,
    SupervisedExecutionState,
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

NOW = datetime(2026, 7, 30, 16, 0, tzinfo=UTC)


def request(
    agent_id: str = "worker", capability: str = "analysis"
) -> AgentExecutionRequest:
    return AgentExecutionRequest(
        execution_id="execution-1",
        agent_id=AgentId(value=agent_id),
        capability=AgentCapability(id=capability),
        input={"brief": "content"},
        context={"objective": "Analyze"},
        workflow_execution_id="run-1",
        workflow_step_id="analyze",
    )


def result(
    status: AgentExecutionStatus,
    *,
    agent_id: str = "worker",
    metadata=None,
) -> AgentExecutionResult:
    return AgentExecutionResult(
        execution_id="execution-1",
        agent_id=AgentId(value=agent_id),
        status=status,
        started_at=NOW,
        completed_at=NOW,
        duration_seconds=0,
        attempts=1,
        error=(
            None
            if status is AgentExecutionStatus.SUCCEEDED
            else AgentError(code="agent_failure", message="Failed.")
        ),
        metadata=metadata or {},
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


class FakeRuntime:
    def __init__(self, failures=0, exception=None) -> None:
        self.failures = failures
        self.exception = exception
        self.calls = 0
        self.requests = []

    def execute(self, execution_request):
        self.calls += 1
        self.requests.append(execution_request)
        if self.exception is not None and self.calls <= self.failures:
            raise self.exception
        failed = self.calls <= self.failures
        return AgentExecutionResult(
            execution_id=execution_request.execution_id,
            agent_id=execution_request.agent_id,
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
                AgentError(code="agent_failure", message="Failed.")
                if failed
                else None
            ),
            metadata=execution_request.metadata,
        )


def supervisor(
    runtime,
    policy=None,
    *,
    sleeper=lambda _: None,
):
    repository, recorder = timeline()
    metrics = InMemoryRecoveryMetrics()
    recovery = ExecutionRecoveryService(
        timeline=recorder,
        metrics=metrics,
        policy=policy,
        clock=lambda: NOW,
        sleeper=sleeper,
    )
    return (
        DefaultExecutionSupervisor(
            runtime,
            recovery,
            timeline=recorder,
            metrics=metrics,
        ),
        repository,
        metrics,
    )


def test_state_machine_validates_transitions_and_history() -> None:
    machine = ExecutionStateMachine()
    machine.transition(SupervisedExecutionState.PLANNING)
    machine.transition(SupervisedExecutionState.READY)
    machine.transition(SupervisedExecutionState.RUNNING)
    machine.transition(SupervisedExecutionState.SUCCEEDED)

    assert machine.state is SupervisedExecutionState.SUCCEEDED
    assert machine.history == (
        SupervisedExecutionState.PENDING,
        SupervisedExecutionState.PLANNING,
        SupervisedExecutionState.READY,
        SupervisedExecutionState.RUNNING,
        SupervisedExecutionState.SUCCEEDED,
    )
    with pytest.raises(InvalidStateTransitionError):
        machine.transition(SupervisedExecutionState.RUNNING)


@pytest.mark.parametrize(
    ("failure", "category"),
    [
        (TimeoutError(), FailureCategory.TIMEOUT),
        (OSError(), FailureCategory.INFRASTRUCTURE),
        (ValueError(), FailureCategory.UNEXPECTED),
        (
            result(AgentExecutionStatus.REJECTED),
            FailureCategory.VALIDATION,
        ),
        (
            result(AgentExecutionStatus.TIMED_OUT),
            FailureCategory.TIMEOUT,
        ),
        (
            result(AgentExecutionStatus.FAILED),
            FailureCategory.AGENT,
        ),
    ],
)
def test_failure_classifier(failure, category) -> None:
    assert FailureClassifier().classify(failure) is category


def test_classifier_rejects_success() -> None:
    with pytest.raises(FailureClassificationError):
        FailureClassifier().classify(
            result(AgentExecutionStatus.SUCCEEDED)
        )


def test_retry_policy_is_bounded_and_deterministic() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        eligible_failures=(FailureCategory.AGENT,),
    )

    assert policy.decide(FailureCategory.AGENT, 1) is RetryDecision.RETRY
    assert policy.decide(
        FailureCategory.CONFIGURATION, 1
    ) is RetryDecision.DO_NOT_RETRY
    assert policy.decide(
        FailureCategory.AGENT, 3
    ) is RetryDecision.LIMIT_EXCEEDED
    with pytest.raises(ValidationError):
        RetryPolicy(max_attempts=101)


def test_backoff_strategies_and_limit() -> None:
    policy = RetryPolicy(
        max_attempts=4,
        interval_seconds=2,
        max_delay_seconds=5,
    )

    assert ConstantBackoff().delay(3, policy) == 2
    assert LinearBackoff().delay(3, policy) == 5
    assert ExponentialBackoff().delay(3, policy) == 5


def test_fallback_policy_requires_target() -> None:
    with pytest.raises(ValidationError):
        FallbackPolicy(action=FallbackAction.SUBSTITUTE_AGENT)
    with pytest.raises(ValidationError):
        FallbackPolicy(action=FallbackAction.ALTERNATIVE_STEP)


def test_recovery_validator_rejects_impossible_fallback() -> None:
    context = RecoveryContext(
        request=request(), agent_id=AgentId(value="worker")
    )
    policy = RecoveryPolicy(
        fallback=FallbackPolicy(
            action=FallbackAction.SUBSTITUTE_AGENT,
            replacement_agent_id=AgentId(value="worker"),
        )
    )

    with pytest.raises(RecoveryPolicyError):
        RecoveryValidator().validate(context, policy)


def test_supervisor_success_records_timeline_and_metrics() -> None:
    runtime = FakeRuntime()
    execution_supervisor, repository, metrics = supervisor(runtime)

    execution_result = execution_supervisor.execute(request())

    assert execution_result.status is AgentExecutionStatus.SUCCEEDED
    assert metrics.snapshot().executions_succeeded == 1
    assert [event.type for event in repository.list_by_run("run-1")] == [
        TimelineEventType.EXECUTION_STARTED,
        TimelineEventType.EXECUTION_COMPLETED,
    ]


def test_supervisor_retries_with_backoff_then_succeeds() -> None:
    delays = []
    runtime = FakeRuntime(failures=1)
    execution_supervisor, repository, metrics = supervisor(
        runtime,
        RecoveryPolicy(
            retry=RetryPolicy(
                max_attempts=2,
                interval_seconds=3,
                backoff=BackoffKind.LINEAR,
            )
        ),
        sleeper=delays.append,
    )

    execution_result = execution_supervisor.execute(request())

    assert execution_result.status is AgentExecutionStatus.SUCCEEDED
    assert runtime.calls == 2
    assert delays == [3]
    assert metrics.snapshot().retries_total == 1
    types = [event.type for event in repository.list_by_run("run-1")]
    assert TimelineEventType.RETRY_STARTED in types
    assert TimelineEventType.RETRY_COMPLETED in types


def test_retry_limit_applies_fail_fallback() -> None:
    runtime = FakeRuntime(failures=3)
    execution_supervisor, repository, metrics = supervisor(
        runtime,
        RecoveryPolicy(retry=RetryPolicy(max_attempts=2)),
    )

    execution_result = execution_supervisor.execute(request())

    assert execution_result.status is AgentExecutionStatus.FAILED
    assert runtime.calls == 2
    assert metrics.snapshot().executions_failed == 1
    assert repository.list_by_run("run-1")[-1].type is (
        TimelineEventType.EXECUTION_FAILED
    )


def test_ignore_step_fallback_converts_failure_to_success() -> None:
    runtime = FakeRuntime(failures=1)
    execution_supervisor, _, metrics = supervisor(
        runtime,
        RecoveryPolicy(
            fallback=FallbackPolicy(
                action=FallbackAction.IGNORE_STEP
            )
        ),
    )

    execution_result = execution_supervisor.execute(request())

    assert execution_result.status is AgentExecutionStatus.SUCCEEDED
    assert execution_result.output["fallback"] == "ignored_step"
    assert metrics.snapshot().fallbacks_total == 1


def test_substitute_agent_fallback_uses_replacement() -> None:
    runtime = FakeRuntime(failures=1)
    execution_supervisor, _, metrics = supervisor(
        runtime,
        RecoveryPolicy(
            fallback=FallbackPolicy(
                action=FallbackAction.SUBSTITUTE_AGENT,
                replacement_agent_id=AgentId(value="backup"),
            )
        ),
    )

    execution_result = execution_supervisor.execute(request())

    assert execution_result.status is AgentExecutionStatus.SUCCEEDED
    assert runtime.requests[-1].agent_id == AgentId(value="backup")
    assert metrics.snapshot().average_retry_count == 0


def test_cancel_workflow_fallback_returns_cancelled_result() -> None:
    runtime = FakeRuntime(failures=1)
    execution_supervisor, repository, _ = supervisor(
        runtime,
        RecoveryPolicy(
            fallback=FallbackPolicy(
                action=FallbackAction.CANCEL_WORKFLOW
            )
        ),
    )

    execution_result = execution_supervisor.execute(request())

    assert execution_result.status is AgentExecutionStatus.CANCELLED
    assert repository.list_by_run("run-1")[-1].type is (
        TimelineEventType.EXECUTION_CANCELLED
    )


def test_alternative_step_fallback_changes_capability() -> None:
    runtime = FakeRuntime(failures=1)
    execution_supervisor, _, _ = supervisor(
        runtime,
        RecoveryPolicy(
            fallback=FallbackPolicy(
                action=FallbackAction.ALTERNATIVE_STEP,
                alternative_capability="review",
            )
        ),
    )

    execution_result = execution_supervisor.execute(request())

    assert execution_result.status is AgentExecutionStatus.SUCCEEDED
    assert runtime.requests[-1].capability.id == "review"


class RegisteredAgent:
    def __init__(self, agent_id, capability) -> None:
        self.metadata = AgentMetadata(
            id=AgentId(value=agent_id),
            name=agent_id,
            description="Recovery integration agent.",
            version="1.0",
            capabilities=(AgentCapability(id=capability),),
        )

    def execute(self, request, context):  # pragma: no cover
        raise AssertionError("AgentCoordinator deve usar Runtime.")


def coordinated_plan(capability="analysis") -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-recovery",
        goal="Recover",
        steps=(
            PlanStep(
                step_id="analyze",
                description="Analyze",
                required_capability=capability,
            ),
        ),
        estimated_cost=1,
        estimated_duration_seconds=1,
        created_at=NOW,
    )


def test_coordinator_uses_supervisor_as_agent_runtime() -> None:
    raw_runtime = FakeRuntime(failures=1)
    execution_supervisor, _, _ = supervisor(
        raw_runtime,
        RecoveryPolicy(retry=RetryPolicy(max_attempts=2)),
    )
    registry = InMemoryAgentRegistry()
    registry.register(RegisteredAgent("worker", "analysis"))
    _, coordinator_timeline = timeline()
    coordinator = AgentCoordinator(
        registry,
        execution_supervisor,
        timeline=coordinator_timeline,
        clock=lambda: NOW,
    )

    coordination_result = coordinator.coordinate(
        CoordinationContext(
            execution_plan=coordinated_plan(),
            metadata={"run_id": "run-1"},
        )
    )

    assert coordination_result.status.value == "completed"
    assert raw_runtime.calls == 2


@dataclass
class WorkflowStep:
    id: str

    def execute(self, context):
        assert context.values["coordination_result"]["status"] == "completed"


def test_full_workflow_planning_coordination_supervision_recovery() -> None:
    raw_runtime = FakeRuntime(failures=1)
    execution_supervisor, _, _ = supervisor(
        raw_runtime,
        RecoveryPolicy(retry=RetryPolicy(max_attempts=2)),
    )
    registry = InMemoryAgentRegistry()
    registry.register(RegisteredAgent("worker", "workflow_step"))
    _, coordination_timeline = timeline()
    coordinator = AgentCoordinator(
        registry,
        execution_supervisor,
        timeline=coordination_timeline,
        clock=lambda: NOW,
    )
    _, planning_timeline = timeline()
    _, workflow_timeline = timeline()
    engine = WorkflowEngine(
        WorkflowValidator(),
        WorkflowExecutor(workflow_timeline, clock=lambda: NOW),
        planner=PlanningEngine(
            timeline=planning_timeline, clock=lambda: NOW
        ),
        coordinator=coordinator,
    )

    workflow_result = engine.execute(
        WorkflowDefinition(
            id="recovery-workflow", steps=(WorkflowStep("analyze"),)
        ),
        WorkflowContext(run_id="run-1"),
    )

    assert workflow_result.context.values["coordination_result"][
        "status"
    ] == "completed"
    assert raw_runtime.calls == 2
