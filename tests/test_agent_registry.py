from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from asep.agents import (
    AgentAlreadyRegisteredException,
    AgentCapability,
    AgentId,
    AgentMetadata,
    AgentNotFoundException,
    AgentRegistry,
    AgentRequest,
    AgentStatus,
    AgentStepAdapter,
    AgentValidationException,
    InMemoryAgentRegistry,
    InvalidAgentRegistrationException,
)
from asep.execution.models import AgentContext, AgentResult
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder
from asep.workflow import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowExecutor,
    WorkflowStatus,
    WorkflowValidator,
)

NOW = datetime(2026, 7, 30, 20, 0, tzinfo=UTC)


class FakeAgent:
    def __init__(
        self,
        agent_id: str,
        *capabilities: str,
        error: Exception | None = None,
    ) -> None:
        self._metadata = AgentMetadata(
            id=AgentId(value=agent_id),
            name=agent_id.title(),
            description=f"Fake agent {agent_id}.",
            version="1.0.0",
            capabilities=tuple(
                AgentCapability(id=item) for item in capabilities
            ),
        )
        self.error = error
        self.calls = 0

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def execute(
        self,
        request: AgentRequest,
        context: AgentContext,
    ) -> AgentResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return AgentResult(
            status=AgentStatus.COMPLETED,
            agent_id=context.agent_id,
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=context.started_at,
            finished_at=NOW,
            metadata={"request_id": request.request_id},
        )


class InvalidMetadataAgent:
    metadata = {"id": "invalid"}

    def execute(self, request: Any, context: Any) -> None:
        del request, context


class MissingExecuteAgent:
    metadata = AgentMetadata(
        id=AgentId(value="missing-execute"),
        name="Missing Execute",
        description="Invalid test object.",
        version="1",
    )


def aid(value: str) -> AgentId:
    return AgentId(value=value)


def test_registry_protocol_is_structural_and_empty_queries_are_safe() -> None:
    registry = InMemoryAgentRegistry()

    assert isinstance(registry, AgentRegistry)
    assert registry.list_all() == ()
    assert registry.find_by_capability(AgentCapability(id="testing")) == ()
    assert not registry.contains(aid("missing"))


def test_register_get_contains_and_metadata() -> None:
    registry = InMemoryAgentRegistry()
    agent = FakeAgent("tester", "testing")

    registry.register(agent)

    assert registry.contains(aid("tester"))
    assert registry.get(aid("tester")) is agent
    assert registry.get_metadata(aid("tester")) is agent.metadata


@pytest.mark.parametrize(
    "agent",
    [None, InvalidMetadataAgent(), MissingExecuteAgent()],
)
def test_rejects_invalid_agent_registration(agent: object) -> None:
    registry = InMemoryAgentRegistry()

    with pytest.raises(InvalidAgentRegistrationException):
        registry.register(agent)  # type: ignore[arg-type]


def test_rejects_invalid_agent_id_argument() -> None:
    registry = InMemoryAgentRegistry()

    with pytest.raises(InvalidAgentRegistrationException, match="AgentId"):
        registry.get("tester")  # type: ignore[arg-type]


def test_duplicate_id_is_rejected_and_original_is_preserved() -> None:
    registry = InMemoryAgentRegistry()
    original = FakeAgent("tester", "testing")
    duplicate = FakeAgent("tester", "documentation")
    registry.register(original)

    with pytest.raises(AgentAlreadyRegisteredException) as captured:
        registry.register(duplicate)

    assert captured.value.agent_id == aid("tester")
    assert registry.get(aid("tester")) is original


def test_missing_agent_raises_specific_error() -> None:
    with pytest.raises(AgentNotFoundException) as captured:
        InMemoryAgentRegistry().get(aid("missing"))

    assert captured.value.agent_id == aid("missing")


def test_list_all_is_sorted_by_agent_id_and_returns_snapshot() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(FakeAgent("zeta"))
    registry.register(FakeAgent("alpha"))

    listed = registry.list_all()

    assert tuple(str(agent.metadata.id) for agent in listed) == (
        "alpha",
        "zeta",
    )
    assert isinstance(listed, tuple)
    assert registry.list_all() == listed


def test_find_by_capability_is_case_sensitive_sorted_and_supports_multiple() -> None:
    registry = InMemoryAgentRegistry()
    documentation = FakeAgent("documentation", "writing", "review")
    testing = FakeAgent("testing", "testing", "review")
    registry.register(testing)
    registry.register(documentation)

    found = registry.find_by_capability(AgentCapability(id="review"))

    assert found == (documentation, testing)
    assert registry.find_by_capability(AgentCapability(id="Review")) == ()
    assert registry.find_by_capability(AgentCapability(id="missing")) == ()


def test_unregister_removes_agent_and_allows_registration_again() -> None:
    registry = InMemoryAgentRegistry()
    original = FakeAgent("tester")
    replacement = FakeAgent("tester", "testing")
    registry.register(original)

    registry.unregister(aid("tester"))
    registry.register(replacement)

    assert registry.get(aid("tester")) is replacement


def test_unregister_missing_agent_raises_specific_error() -> None:
    with pytest.raises(AgentNotFoundException):
        InMemoryAgentRegistry().unregister(aid("missing"))


def test_registry_instances_have_isolated_lifecycle() -> None:
    first = InMemoryAgentRegistry()
    second = InMemoryAgentRegistry()
    first.register(FakeAgent("tester"))

    assert first.contains(aid("tester"))
    assert not second.contains(aid("tester"))


@dataclass
class CommonStep:
    id: str = "common"

    def execute(self, context: WorkflowContext) -> None:
        context.values["shared"] = "from-common-step"


def agent_context() -> AgentContext:
    return AgentContext(
        run_id="run-1",
        project_id="project",
        project_name="Project",
        workflow_id="workflow",
        stage_id="agent-step",
        agent_id="tester",
        started_at=NOW,
        objective="Test",
        scope_received="Shared context",
    )


def engine() -> WorkflowEngine:
    return WorkflowEngine(
        WorkflowValidator(),
        WorkflowExecutor(
            TimelineRecorder(InMemoryTimelineRepository()),
        ),
    )


def test_registered_agent_integrates_with_common_step_and_workflow() -> None:
    registry = InMemoryAgentRegistry()
    agent = FakeAgent("tester", "testing")
    registry.register(agent)
    context = WorkflowContext(run_id="run-1")
    workflow = WorkflowDefinition(
        id="mixed",
        steps=(
            CommonStep(),
            AgentStepAdapter(
                step_id="agent-step",
                agent=registry.get(aid("tester")),
                request=AgentRequest(
                    request_id="request-1",
                    objective="Test shared execution",
                    inputs={"source": "workflow"},
                ),
                context=agent_context(),
            ),
        ),
    )

    result = engine().execute(workflow, context)

    assert result.status is WorkflowStatus.COMPLETED
    assert result.completed_steps == ("common", "agent-step")
    assert result.context.values["shared"] == "from-common-step"
    assert result.context.values["agent_results.agent-step"].metadata == {
        "request_id": "request-1"
    }
    assert result.metrics["completed_steps"] == 2
    assert len(result.timeline) == 4
    assert agent.calls == 1


def test_failure_from_registered_agent_becomes_workflow_failure() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(FakeAgent("tester", error=RuntimeError("failure")))
    workflow = WorkflowDefinition(
        id="failure",
        steps=(
            AgentStepAdapter(
                step_id="agent-step",
                agent=registry.get(aid("tester")),
                request=AgentRequest(
                    request_id="request-1",
                    objective="Fail safely",
                ),
                context=agent_context(),
            ),
        ),
    )

    result = engine().execute(workflow, WorkflowContext(run_id="run-1"))

    assert result.status is WorkflowStatus.FAILED
    assert result.failed_steps == ("agent-step",)
    assert result.metrics["failed_steps"] == 1
    assert result.error is not None
    assert result.error.type == "AgentExecutionException"


def test_adapter_still_validates_agent_resolved_from_registry() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(FakeAgent("tester"))
    context = agent_context().model_copy(update={"agent_id": "other"})

    with pytest.raises(AgentValidationException, match="AgentContext"):
        AgentStepAdapter(
            step_id="agent-step",
            agent=registry.get(aid("tester")),
            request=AgentRequest(
                request_id="request-1",
                objective="Invalid identity",
            ),
            context=context,
        )
