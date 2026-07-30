from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import inspect

import pytest

from asep.timeline import InMemoryTimelineRepository, TimelineRecorder
from asep.workflow import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowExecutionPolicy,
    WorkflowExecutor,
    WorkflowStatus,
    WorkflowStepException,
    WorkflowStepExecutor,
    WorkflowValidationException,
    WorkflowValidator,
)

NOW = datetime(2026, 7, 30, 15, 0, tzinfo=UTC)


@dataclass
class Step:
    id: str
    value: str | None = None
    error: Exception | None = None
    cancel: bool = False

    def execute(self, context: WorkflowContext) -> None:
        context.values.setdefault("order", []).append(self.id)
        if self.value is not None:
            context.values["result"] = self.value
        if self.cancel:
            context.request_cancellation()
        if self.error is not None:
            raise self.error


def recorder() -> TimelineRecorder:
    counter = 0

    def event_id() -> str:
        nonlocal counter
        counter += 1
        return f"event-{counter}"

    return TimelineRecorder(
        InMemoryTimelineRepository(),
        clock=lambda: NOW,
        id_generator=event_id,
    )


def engine() -> WorkflowEngine:
    return WorkflowEngine(
        WorkflowValidator(),
        WorkflowExecutor(recorder(), clock=lambda: NOW),
    )


@pytest.mark.parametrize(
    ("workflow", "message"),
    [
        (None, "não pode ser nulo"),
        (WorkflowDefinition(id="", steps=(Step("step"),)), "id não vazio"),
        (WorkflowDefinition(id="wf", steps=()), "ao menos uma Step"),
        (
            WorkflowDefinition(
                id="wf",
                steps=(Step("same"), Step("same")),
            ),
            "duplicados",
        ),
        (
            WorkflowDefinition(
                id="wf",
                steps=(object(),),  # type: ignore[arg-type]
            ),
            "inválida",
        ),
    ],
)
def test_validator_rejects_invalid_workflows(
    workflow: WorkflowDefinition | None,
    message: str,
) -> None:
    with pytest.raises(WorkflowValidationException, match=message):
        WorkflowValidator().validate(workflow)


def test_validator_rejects_unsupported_policy() -> None:
    workflow = WorkflowDefinition(
        id="wf",
        steps=(Step("step"),),
        policy=WorkflowExecutionPolicy(stop_on_failure=False),
    )

    with pytest.raises(
        WorkflowValidationException,
        match="não é suportada",
    ):
        WorkflowValidator().validate(workflow)


def test_step_executor_wraps_original_exception() -> None:
    original = RuntimeError("failure")

    with pytest.raises(WorkflowStepException) as captured:
        WorkflowStepExecutor().execute(
            Step("broken", error=original),
            WorkflowContext(run_id="run"),
        )

    assert captured.value.step_id == "broken"
    assert captured.value.cause is original


def test_executor_shares_context_and_returns_rich_result() -> None:
    context = WorkflowContext(run_id="run")
    workflow = WorkflowDefinition(
        id="wf",
        description="demonstration",
        metadata={"owner": "qa"},
        steps=(Step("one"), Step("two", value="done")),
    )

    result = engine().execute(workflow, context)

    assert result.status is WorkflowStatus.COMPLETED
    assert result.executed_steps == ("one", "two")
    assert result.failed_steps == ()
    assert result.context.values["order"] == ["one", "two"]
    assert result.final_result == "done"
    assert result.metrics == {
        "total_steps": 2,
        "completed_steps": 2,
        "failed_steps": 0,
        "duration_seconds": 0,
    }
    assert len(result.timeline) == 4


def test_engine_returns_structured_step_failure() -> None:
    result = engine().execute(
        WorkflowDefinition(
            id="wf",
            steps=(
                Step("ok"),
                Step("broken", error=ValueError("invalid")),
                Step("not-run"),
            ),
        ),
        WorkflowContext(run_id="run"),
    )

    assert result.status is WorkflowStatus.FAILED
    assert result.completed_steps == ("ok",)
    assert result.failed_steps == ("broken",)
    assert result.executed_steps == ("ok", "broken")
    assert result.error is not None
    assert result.error.type == "ValueError"
    assert result.metrics["failed_steps"] == 1


def test_engine_stops_on_cooperative_cancellation() -> None:
    context = WorkflowContext(run_id="run")

    result = engine().execute(
        WorkflowDefinition(
            id="wf",
            steps=(Step("cancel", cancel=True), Step("not-run")),
        ),
        context,
    )

    assert result.status is WorkflowStatus.CANCELLED
    assert result.executed_steps == ()
    assert context.values["order"] == ["cancel"]
    assert len(result.timeline) == 3


def test_engine_accepts_cancellation_disabled_policy() -> None:
    context = WorkflowContext(run_id="run")
    result = engine().execute(
        WorkflowDefinition(
            id="wf",
            steps=(Step("request", cancel=True), Step("continues")),
            policy=WorkflowExecutionPolicy(allow_cancellation=False),
        ),
        context,
    )

    assert result.status is WorkflowStatus.COMPLETED
    assert result.completed_steps == ("request", "continues")


def test_definition_keeps_description_metadata_and_policy() -> None:
    definition = WorkflowDefinition(
        id="wf",
        description="description",
        metadata={"team": "platform"},
        steps=(Step("step"),),
    )

    validated = WorkflowValidator().validate(definition)

    assert validated is definition
    assert validated.description == "description"
    assert validated.metadata == {"team": "platform"}


def test_orchestrator_delegates_without_iterating_steps() -> None:
    import asep.workflow.orchestrator as module

    source = inspect.getsource(module.WorkflowOrchestrator.execute)

    assert "self._engine.execute(workflow, context)" in source
    assert "for step in" not in source
    assert ".execute(context)" not in source
