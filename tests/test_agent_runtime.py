import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Thread

import pytest
from pydantic import ValidationError

from asep.agents import (
    AgentCapability,
    AgentCapabilityNotSupportedError,
    AgentDuplicateExecutionError,
    AgentExecutionFailedError,
    AgentExecutionPolicy,
    AgentExecutionRequest,
    AgentExecutionService,
    AgentExecutionStatus,
    AgentId,
    AgentMetadata,
    AgentNotRegisteredError,
    AgentRetryExhaustedError,
    AgentRuntime as IntelligentAgentRuntime,
    AgentStatus,
    AgentStepAdapter,
    InMemoryAgentExecutionMetrics,
    InMemoryAgentRegistry,
)
from asep.agents.business_analyst import BusinessAnalystAgent
from asep.errors import AgentNotFoundError, AgentResultError
from asep.execution.models import AgentContext, AgentResult, AgentResultStatus
from asep.registry.loader import RegistryLoader
from asep.runtime.agent_runtime import AgentRuntime as LegacyAgentRuntime
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
    WorkflowStatus,
    WorkflowValidator,
)


def context(agent_id: str = "business-analyst") -> AgentContext:
    return AgentContext(
        run_id="f2f1a9f1-2c60-4fa0-9120-6b9197589488",
        project_id="sample",
        project_name="Sample",
        workflow_id="software-project",
        stage_id="intake",
        agent_id=agent_id,
        started_at=datetime(2026, 7, 28, tzinfo=UTC),
        objective="Objetivo confirmado",
        scope_received="Escopo confirmado",
    )


def test_business_analyst_is_deterministic_and_creates_markdown() -> None:
    result = BusinessAnalystAgent().execute(context())

    assert result.status == AgentResultStatus.COMPLETED
    assert result.artifacts[0].relative_path.endswith(".md")
    assert result.run_id in result.artifacts[0].content


def test_business_analyst_blocks_without_required_input() -> None:
    result = BusinessAnalystAgent().execute(
        context().model_copy(update={"objective": None})
    )

    assert result.status == AgentResultStatus.BLOCKED
    assert result.artifacts == []
    assert result.metadata["missing_inputs"] == ["objective"]


def test_runtime_rejects_agent_without_adapter(sample_repository: Path) -> None:
    registry = RegistryLoader().load(sample_repository / "registry")

    with pytest.raises(AgentNotFoundError):
        LegacyAgentRuntime({}).execute(
            context(),
            registry,
            logging.getLogger("test"),
        )


def test_runtime_rejects_result_with_wrong_identity(
    sample_repository: Path,
) -> None:
    class InvalidAgent:
        id = "business-analyst"

        def execute(self, agent_context):
            result = BusinessAnalystAgent().execute(agent_context)
            return result.model_copy(update={"run_id": "wrong"})

    registry = RegistryLoader().load(sample_repository / "registry")

    with pytest.raises(AgentResultError):
        LegacyAgentRuntime({"business-analyst": InvalidAgent()}).execute(
            context(), registry, logging.getLogger("test")
        )


NOW = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)


class IntelligentFakeAgent:
    def __init__(
        self,
        *,
        failures: int = 0,
        failure_retryable: bool = False,
        status: AgentStatus = AgentStatus.COMPLETED,
        entered: Event | None = None,
        release: Event | None = None,
    ) -> None:
        self._metadata = AgentMetadata(
            id=AgentId(value="reviewer"),
            name="Reviewer",
            description="Deterministic runtime fake.",
            version="1.0",
            capabilities=(
                AgentCapability(id="review"),
                AgentCapability(id="testing"),
            ),
        )
        self.failures = failures
        self.failure_retryable = failure_retryable
        self.status = status
        self.entered = entered
        self.release = release
        self.calls = 0
        self.contexts: list[AgentContext] = []

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def execute(self, request, agent_context: AgentContext) -> AgentResult:
        del request
        self.calls += 1
        self.contexts.append(agent_context)
        if self.entered is not None:
            self.entered.set()
        if self.release is not None:
            self.release.wait(timeout=2)
        if self.calls <= self.failures:
            raise AgentExecutionFailedError(
                "reviewer",
                error_type="TemporaryFailure",
                retryable=self.failure_retryable,
            )
        return AgentResult(
            status=self.status,
            agent_id="reviewer",
            stage_id=agent_context.stage_id,
            run_id=agent_context.run_id,
            started_at=agent_context.started_at,
            finished_at=NOW,
            messages=["done"],
        )


class Clock:
    def __init__(self, *values: datetime) -> None:
        self._values = iter(values)
        self._last = values[-1]

    def __call__(self) -> datetime:
        return next(self._values, self._last)


def intelligent_request(
    *,
    execution_id: str = "execution-1",
    agent_id: str = "reviewer",
    capability: str = "review",
    timeout_seconds: float | None = None,
    cancellation_requested: bool = False,
    metadata: dict | None = None,
) -> AgentExecutionRequest:
    return AgentExecutionRequest(
        execution_id=execution_id,
        agent_id=AgentId(value=agent_id),
        capability=AgentCapability(id=capability),
        input={"document": "content", "password": "input-secret"},
        context={
            "project_id": "project",
            "project_name": "Project",
            "workflow_id": "workflow",
            "objective": "Review",
            "scope_received": "Document",
        },
        workflow_execution_id="run-1",
        workflow_step_id="review-step",
        correlation_id="correlation-1",
        metadata=metadata or {},
        timeout_seconds=timeout_seconds,
        cancellation_requested=cancellation_requested,
    )


def intelligent_runtime(
    agent: IntelligentFakeAgent | None = None,
    *,
    policy: AgentExecutionPolicy | None = None,
    clock: Clock | None = None,
) -> tuple[
    AgentExecutionService,
    InMemoryTimelineRepository,
    InMemoryAgentExecutionMetrics,
    InMemoryAgentRegistry,
]:
    registry = InMemoryAgentRegistry()
    if agent is not None:
        registry.register(agent)
    timeline_repository = InMemoryTimelineRepository()
    metrics = InMemoryAgentExecutionMetrics()
    counter = 0

    def event_id() -> str:
        nonlocal counter
        counter += 1
        return f"event-{counter}"

    service = AgentExecutionService(
        registry,
        timeline=TimelineRecorder(
            timeline_repository,
            clock=clock or Clock(NOW),
            id_generator=event_id,
        ),
        metrics=metrics,
        policy=policy,
        clock=clock or Clock(NOW),
    )
    return service, timeline_repository, metrics, registry


def test_intelligent_runtime_success_preserves_correlation_and_metrics() -> None:
    agent = IntelligentFakeAgent()
    service, timeline, metrics, _ = intelligent_runtime(agent)

    result = service.execute(intelligent_request())

    assert isinstance(service, IntelligentAgentRuntime)
    assert result.status is AgentExecutionStatus.SUCCEEDED
    assert result.execution_id == "execution-1"
    assert result.agent_id == AgentId(value="reviewer")
    assert result.attempts == 1
    assert result.agent_result is not None
    assert agent.contexts[0].run_id == "run-1"
    assert agent.contexts[0].stage_id == "review-step"
    events = timeline.list_by_run("run-1")
    assert tuple(event.type for event in events) == (
        TimelineEventType.AGENT_EXECUTION_REQUESTED,
        TimelineEventType.AGENT_EXECUTION_VALIDATED,
        TimelineEventType.AGENT_EXECUTION_STARTED,
        TimelineEventType.AGENT_EXECUTION_SUCCEEDED,
    )
    assert metrics.snapshot().succeeded == 1
    assert metrics.snapshot().by_agent == {"reviewer": 1}
    assert metrics.snapshot().by_capability == {"review": 1}


@pytest.mark.parametrize(
    ("execution_request", "error_type"),
    [
        (intelligent_request(agent_id="missing"), AgentNotRegisteredError),
        (
            intelligent_request(capability="unsupported"),
            AgentCapabilityNotSupportedError,
        ),
    ],
)
def test_validation_rejects_missing_agent_or_capability(
    execution_request: AgentExecutionRequest,
    error_type: type[Exception],
) -> None:
    agent = IntelligentFakeAgent()
    service, timeline, metrics, _ = intelligent_runtime(agent)

    with pytest.raises(error_type):
        service.execute(execution_request)

    assert timeline.list_by_run("run-1")[-1].type is (
        TimelineEventType.AGENT_EXECUTION_REJECTED
    )
    assert metrics.snapshot().rejected == 1
    assert agent.calls == 0


def test_validation_can_return_structured_rejection_when_not_fail_fast() -> None:
    service, _, _, _ = intelligent_runtime(
        IntelligentFakeAgent(),
        policy=AgentExecutionPolicy(fail_fast=False),
    )

    result = service.execute(
        intelligent_request(capability="unsupported")
    )

    assert result.status is AgentExecutionStatus.REJECTED
    assert result.error is not None
    assert result.error.code == "validation_rejected"


def test_failed_agent_is_structured_without_fail_fast() -> None:
    service, _, metrics, _ = intelligent_runtime(
        IntelligentFakeAgent(failures=1),
        policy=AgentExecutionPolicy(fail_fast=False),
    )

    result = service.execute(intelligent_request())

    assert result.status is AgentExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.metadata == {"error_type": "TemporaryFailure"}
    assert metrics.snapshot().failed == 1


def test_fail_fast_preserves_typed_failure_without_secret_message() -> None:
    service, timeline, _, _ = intelligent_runtime(
        IntelligentFakeAgent(failures=1),
    )

    with pytest.raises(AgentExecutionFailedError) as captured:
        service.execute(
            intelligent_request(
                metadata={"password": "do-not-leak"},
            )
        )

    assert "do-not-leak" not in str(captured.value)
    assert "do-not-leak" not in repr(
        timeline.list_by_run("run-1")
    )


def test_retry_disabled_executes_once() -> None:
    agent = IntelligentFakeAgent(
        failures=2,
        failure_retryable=True,
    )
    service, _, _, _ = intelligent_runtime(
        agent,
        policy=AgentExecutionPolicy(fail_fast=False),
    )

    result = service.execute(intelligent_request())

    assert result.status is AgentExecutionStatus.FAILED
    assert agent.calls == 1


def test_retry_enabled_succeeds_and_records_retry() -> None:
    agent = IntelligentFakeAgent(
        failures=1,
        failure_retryable=True,
    )
    service, timeline, metrics, _ = intelligent_runtime(
        agent,
        policy=AgentExecutionPolicy(
            retry_enabled=True,
            max_attempts=2,
            fail_fast=False,
        ),
    )

    result = service.execute(intelligent_request())

    assert result.status is AgentExecutionStatus.SUCCEEDED
    assert result.attempts == 2
    assert agent.calls == 2
    assert metrics.snapshot().retries == 1
    assert TimelineEventType.AGENT_EXECUTION_RETRYING in {
        event.type for event in timeline.list_by_run("run-1")
    }


def test_retry_exhaustion_raises_when_fail_fast() -> None:
    service, _, _, _ = intelligent_runtime(
        IntelligentFakeAgent(
            failures=2,
            failure_retryable=True,
        ),
        policy=AgentExecutionPolicy(
            retry_enabled=True,
            max_attempts=2,
        ),
    )

    with pytest.raises(AgentRetryExhaustedError):
        service.execute(intelligent_request())


def test_timeout_is_deterministic_and_does_not_sleep() -> None:
    clock = Clock(
        NOW,
        NOW,
        NOW,
        NOW + timedelta(seconds=2),
        NOW + timedelta(seconds=2),
    )
    service, timeline, metrics, _ = intelligent_runtime(
        IntelligentFakeAgent(),
        clock=clock,
    )

    result = service.execute(
        intelligent_request(timeout_seconds=1)
    )

    assert result.status is AgentExecutionStatus.TIMED_OUT
    assert result.duration_seconds == 2
    assert metrics.snapshot().timed_out == 1
    assert timeline.list_by_run("run-1")[-1].type is (
        TimelineEventType.AGENT_EXECUTION_TIMED_OUT
    )


def test_pre_cancelled_request_does_not_execute_agent() -> None:
    agent = IntelligentFakeAgent()
    service, _, metrics, _ = intelligent_runtime(agent)

    result = service.execute(
        intelligent_request(cancellation_requested=True)
    )

    assert result.status is AgentExecutionStatus.CANCELLED
    assert result.attempts == 0
    assert agent.calls == 0
    assert metrics.snapshot().cancelled == 1


def test_models_are_immutable_validated_and_hide_sensitive_repr() -> None:
    request = intelligent_request(
        metadata={
            "token": "metadata-secret",
            "nested": {"authorization": "credential", "safe": "value"},
        }
    )

    assert "metadata-secret" not in repr(request)
    assert "input-secret" not in repr(request)
    with pytest.raises(ValidationError):
        request.execution_id = "changed"
    with pytest.raises(ValidationError):
        AgentExecutionPolicy(
            retry_enabled=False,
            max_attempts=2,
        )


def test_sensitive_metadata_is_filtered_from_result_and_events() -> None:
    service, timeline, _, _ = intelligent_runtime(
        IntelligentFakeAgent(),
    )
    request = intelligent_request(
        metadata={
            "password": "sensitive-password-value",
            "secret": "sensitive-secret-value",
            "token": "sensitive-token-value",
            "api_key": "sensitive-api-key-value",
            "authorization": "sensitive-authorization-value",
            "nested": {
                "password": "sensitive-nested-value",
                "safe": "kept",
            },
            "safe": "visible",
        }
    )

    result = service.execute(request)
    rendered = repr(timeline.list_by_run("run-1"))

    assert result.metadata == {
        "nested": {"safe": "kept"},
        "safe": "visible",
    }
    for secret in (
        "sensitive-password-value",
        "sensitive-secret-value",
        "sensitive-token-value",
        "sensitive-api-key-value",
        "sensitive-authorization-value",
        "sensitive-nested-value",
    ):
        assert secret not in rendered
        assert secret not in repr(result)


def test_completed_execution_id_is_idempotent_in_same_instance() -> None:
    agent = IntelligentFakeAgent()
    service, timeline, metrics, _ = intelligent_runtime(agent)
    request = intelligent_request()

    first = service.execute(request)
    second = service.execute(request)

    assert second is first
    assert agent.calls == 1
    assert len(timeline.list_by_run("run-1")) == 4
    assert metrics.snapshot().total == 1


def test_simultaneous_duplicate_execution_is_rejected_locally() -> None:
    entered = Event()
    release = Event()
    agent = IntelligentFakeAgent(entered=entered, release=release)
    service, _, _, _ = intelligent_runtime(agent)
    request = intelligent_request()
    results: list = []

    thread = Thread(target=lambda: results.append(service.execute(request)))
    thread.start()
    assert entered.wait(timeout=2)
    try:
        with pytest.raises(AgentDuplicateExecutionError):
            service.execute(request)
    finally:
        release.set()
        thread.join(timeout=2)

    assert len(results) == 1
    assert agent.calls == 1


def test_removed_agent_is_rejected_by_runtime() -> None:
    agent = IntelligentFakeAgent()
    service, _, _, registry = intelligent_runtime(agent)
    registry.unregister(AgentId(value="reviewer"))

    with pytest.raises(AgentNotRegisteredError):
        service.execute(intelligent_request())


def test_runtime_adapter_executes_inside_workflow_engine() -> None:
    service, _, metrics, _ = intelligent_runtime(
        IntelligentFakeAgent(),
    )
    workflow = WorkflowDefinition(
        id="runtime-workflow",
        steps=(
            AgentStepAdapter(
                step_id="review-step",
                runtime=service,
                execution_request=intelligent_request(),
            ),
        ),
    )

    result = WorkflowEngine(
        WorkflowValidator(),
        WorkflowExecutor(
            TimelineRecorder(InMemoryTimelineRepository()),
        ),
    ).execute(workflow, WorkflowContext(run_id="run-1"))

    assert result.status is WorkflowStatus.COMPLETED
    runtime_result = result.context.values["agent_results.review-step"]
    assert runtime_result.status is AgentExecutionStatus.SUCCEEDED
    assert metrics.snapshot().total == 1


def test_existing_business_analyst_runs_through_formal_runtime() -> None:
    agent = BusinessAnalystAgent()
    registry = InMemoryAgentRegistry()
    registry.register(agent)
    timeline = TimelineRecorder(InMemoryTimelineRepository())
    service = AgentExecutionService(registry, timeline=timeline)
    request = AgentExecutionRequest(
        execution_id="business-analysis-1",
        agent_id=AgentId(value="business-analyst"),
        capability=AgentCapability(id="business-analysis"),
        workflow_execution_id="run-business-analysis",
        workflow_step_id="intake",
        context={
            "project_id": "sample",
            "project_name": "Sample",
            "workflow_id": "software-project",
            "objective": "Objetivo confirmado",
            "scope_received": "Escopo confirmado",
        },
    )

    result = service.execute(request)

    assert result.status is AgentExecutionStatus.SUCCEEDED
    assert result.agent_result is not None
    assert result.agent_result.artifacts[0].relative_path.endswith(".md")


def test_runtime_adapter_turns_failed_result_into_workflow_failure() -> None:
    service, _, _, _ = intelligent_runtime(
        IntelligentFakeAgent(status=AgentStatus.FAILED),
        policy=AgentExecutionPolicy(fail_fast=False),
    )
    workflow = WorkflowDefinition(
        id="runtime-failure-workflow",
        steps=(
            AgentStepAdapter(
                step_id="review-step",
                runtime=service,
                execution_request=intelligent_request(),
            ),
        ),
    )

    result = WorkflowEngine(
        WorkflowValidator(),
        WorkflowExecutor(
            TimelineRecorder(InMemoryTimelineRepository()),
        ),
    ).execute(workflow, WorkflowContext(run_id="run-1"))

    assert result.status is WorkflowStatus.FAILED
    runtime_result = result.context.values["agent_results.review-step"]
    assert runtime_result.status is AgentExecutionStatus.FAILED
