from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from asep.agents import (
    Agent,
    AgentCapability,
    AgentExecutionException,
    AgentId,
    AgentMetadata,
    AgentRequest,
    AgentStatus,
    AgentStepAdapter,
    AgentValidationException,
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

NOW = datetime(2026, 7, 30, 18, 0, tzinfo=UTC)


class FakeAgent:
    def __init__(
        self,
        *,
        result: AgentResult | object | None = None,
        error: Exception | None = None,
    ) -> None:
        self._metadata = AgentMetadata(
            id=AgentId(value="reviewer"),
            name="Reviewer",
            description="Reviews an input deterministically.",
            version="1.0.0",
            capabilities=(
                AgentCapability(
                    id="review",
                    description="Review structured input.",
                ),
            ),
        )
        self.result = result
        self.error = error
        self.calls: list[tuple[AgentRequest, AgentContext]] = []

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def execute(
        self,
        request: AgentRequest,
        context: AgentContext,
    ) -> AgentResult | object:
        self.calls.append((request, context))
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def agent_context() -> AgentContext:
    return AgentContext(
        run_id="run-1",
        project_id="project",
        project_name="Project",
        workflow_id="workflow",
        stage_id="review",
        agent_id="reviewer",
        started_at=NOW,
        objective="Review",
        scope_received="Document",
    )


def agent_result(
    *,
    run_id: str = "run-1",
    agent_id: str = "reviewer",
) -> AgentResult:
    return AgentResult(
        status=AgentStatus.COMPLETED,
        agent_id=agent_id,
        stage_id="review",
        run_id=run_id,
        started_at=NOW,
        finished_at=NOW,
        messages=["reviewed"],
    )


def request() -> AgentRequest:
    return AgentRequest(
        request_id="request-1",
        objective="Review the document",
        inputs={"document": "content"},
    )


def test_agent_identity_metadata_capabilities_and_request_are_strict() -> None:
    metadata = FakeAgent(result=agent_result()).metadata

    assert str(metadata.id) == "reviewer"
    assert metadata.capabilities[0].id == "review"
    assert metadata.model_dump(mode="json")["id"] == {"value": "reviewer"}
    assert request().inputs == {"document": "content"}
    with pytest.raises(ValidationError):
        metadata.name = "Changed"

    with pytest.raises(ValueError, match="AgentId"):
        AgentId(value=" ")
    with pytest.raises(ValueError, match="capacidades duplicadas"):
        AgentMetadata(
            id=AgentId(value="agent"),
            name="Agent",
            description="Description",
            version="1",
            capabilities=(
                AgentCapability(id="same"),
                AgentCapability(id="same"),
            ),
        )
    with pytest.raises(ValueError):
        AgentRequest(
            request_id="request",
            objective=" ",
            unsupported=True,
        )


def test_agent_protocol_is_structural() -> None:
    fake = FakeAgent(result=agent_result())

    assert isinstance(fake, Agent)


def test_adapter_executes_agent_and_publishes_result_in_workflow_context() -> None:
    fake = FakeAgent(result=agent_result())
    execution_context = agent_context()
    step = AgentStepAdapter(
        step_id="agent-review",
        agent=fake,
        request=request(),
        context=execution_context,
    )
    workflow_context = WorkflowContext(run_id="run-1")

    step.execute(workflow_context)

    assert fake.calls == [(request(), execution_context)]
    stored = workflow_context.values["agent_results.agent-review"]
    assert stored.status is AgentStatus.COMPLETED


def test_adapter_rejects_context_and_result_identity_mismatch() -> None:
    fake = FakeAgent(result=agent_result(run_id="another-run"))
    step = AgentStepAdapter(
        step_id="agent-review",
        agent=fake,
        request=request(),
        context=agent_context(),
    )

    with pytest.raises(AgentValidationException, match="WorkflowContext"):
        step.execute(WorkflowContext(run_id="wrong-run"))

    with pytest.raises(AgentValidationException, match="AgentResult"):
        step.execute(WorkflowContext(run_id="run-1"))


def test_adapter_wraps_unexpected_agent_failure_without_losing_cause() -> None:
    original = RuntimeError("unavailable")
    step = AgentStepAdapter(
        step_id="agent-review",
        agent=FakeAgent(error=original),
        request=request(),
        context=agent_context(),
    )

    with pytest.raises(AgentExecutionException) as captured:
        step.execute(WorkflowContext(run_id="run-1"))

    assert captured.value.agent_id == "reviewer"
    assert captured.value.cause is original


def test_agent_step_runs_through_workflow_engine_without_engine_coupling() -> None:
    fake = FakeAgent(result=agent_result())
    workflow = WorkflowDefinition(
        id="agent-workflow",
        steps=(
            AgentStepAdapter(
                step_id="agent-review",
                agent=fake,
                request=request(),
                context=agent_context(),
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
    assert result.completed_steps == ("agent-review",)
    assert (
        result.context.values["agent_results.agent-review"].agent_id
        == "reviewer"
    )
