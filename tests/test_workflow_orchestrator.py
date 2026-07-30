from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asep.api import create_app
from asep.application import RunQueryService
from asep.configuration import ApplicationSettings
from asep.metrics import MetricsService
from asep.repositories import RepositoryFactory
from asep.runs import InMemoryRunRepository, Run, RunStatus
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEventType,
)
from asep.workflow import (
    Workflow,
    WorkflowContext,
    WorkflowOrchestrator,
    WorkflowStatus,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


@dataclass
class SimulatedStep:
    id: str
    action: object | None = None

    def execute(self, context: WorkflowContext) -> None:
        context.values.setdefault("order", []).append(self.id)
        if callable(self.action):
            self.action(context)


class RecordingRunRepository(InMemoryRunRepository):
    def __init__(self) -> None:
        super().__init__()
        self.saved: list[Run] = []

    def save(self, run: Run) -> None:
        self.saved.append(run)
        super().save(run)


def id_generator():
    count = 0

    def generate() -> str:
        nonlocal count
        count += 1
        return f"event-{count:03d}"

    return generate


def orchestrator(
    runs: InMemoryRunRepository | None = None,
    timeline: InMemoryTimelineRepository | None = None,
) -> tuple[
    WorkflowOrchestrator,
    InMemoryRunRepository,
    InMemoryTimelineRepository,
]:
    run_repository = runs or InMemoryRunRepository()
    timeline_repository = timeline or InMemoryTimelineRepository()
    service = WorkflowOrchestrator(
        run_repository,
        timeline_repository,
        clock=lambda: NOW,
        event_id_generator=id_generator(),
    )
    return service, run_repository, timeline_repository


def test_executes_single_step_and_returns_completed_result() -> None:
    service, runs, _ = orchestrator()
    context = WorkflowContext(run_id="run")

    result = service.execute(
        Workflow(id="workflow", steps=(SimulatedStep("step"),)),
        context,
    )

    assert result.status is WorkflowStatus.COMPLETED
    assert result.completed_steps == ("step",)
    assert result.context.values == {"order": ["step"]}
    assert runs.get("run").status is RunStatus.SUCCEEDED


def test_executes_multiple_steps_in_declared_order() -> None:
    service, _, _ = orchestrator()
    context = WorkflowContext(run_id="run")
    workflow = Workflow(
        id="workflow",
        steps=tuple(
            SimulatedStep(step_id)
            for step_id in ("first", "second", "third")
        ),
    )

    result = service.execute(workflow, context)

    assert context.values["order"] == ["first", "second", "third"]
    assert result.completed_steps == ("first", "second", "third")


def test_persists_created_running_and_completed_states() -> None:
    runs = RecordingRunRepository()
    service, _, _ = orchestrator(runs=runs)

    service.execute(
        Workflow(id="workflow", steps=(SimulatedStep("step"),)),
        WorkflowContext(run_id="run"),
    )

    assert [run.status for run in runs.saved] == [
        RunStatus.PENDING,
        RunStatus.RUNNING,
        RunStatus.SUCCEEDED,
    ]
    assert [run.metadata["workflow_status"] for run in runs.saved] == [
        "created",
        "running",
        "completed",
    ]


def test_step_failure_stops_workflow_and_returns_structured_error() -> None:
    def fail(context: WorkflowContext) -> None:
        raise RuntimeError("simulated failure")

    service, runs, timeline = orchestrator()
    result = service.execute(
        Workflow(
            id="workflow",
            steps=(
                SimulatedStep("ok"),
                SimulatedStep("broken", fail),
                SimulatedStep("not-run"),
            ),
        ),
        WorkflowContext(run_id="run"),
    )

    assert result.status is WorkflowStatus.FAILED
    assert result.completed_steps == ("ok",)
    assert result.error is not None
    assert result.error.type == "RuntimeError"
    assert result.error.step_id == "broken"
    assert runs.get("run").status is RunStatus.FAILED
    event_types = tuple(
        event.type for event in timeline.list_by_run("run")
    )
    assert TimelineEventType.ERROR in event_types
    assert TimelineEventType.RUN_FINISHED in event_types


def test_cancellation_stops_before_next_step() -> None:
    def cancel(context: WorkflowContext) -> None:
        context.request_cancellation()

    service, runs, timeline = orchestrator()
    context = WorkflowContext(run_id="run")

    result = service.execute(
        Workflow(
            id="workflow",
            steps=(
                SimulatedStep("cancel", cancel),
                SimulatedStep("not-run"),
            ),
        ),
        context,
    )

    assert result.status is WorkflowStatus.CANCELLED
    assert result.completed_steps == ()
    assert context.values["order"] == ["cancel"]
    assert runs.get("run").status is RunStatus.CANCELLED
    assert TimelineEventType.WARNING in tuple(
        event.type for event in timeline.list_by_run("run")
    )


def test_empty_workflow_is_rejected() -> None:
    with pytest.raises(ValueError, match="ao menos uma Step"):
        Workflow(id="workflow", steps=())


def test_timeline_records_full_successful_lifecycle() -> None:
    service, _, timeline = orchestrator()

    service.execute(
        Workflow(
            id="workflow",
            steps=(SimulatedStep("one"), SimulatedStep("two")),
        ),
        WorkflowContext(run_id="run"),
    )

    events = timeline.list_by_run("run")
    assert tuple(event.type for event in events) == (
        TimelineEventType.RUN_STARTED,
        TimelineEventType.STAGE_STARTED,
        TimelineEventType.STAGE_FINISHED,
        TimelineEventType.STAGE_STARTED,
        TimelineEventType.STAGE_FINISHED,
        TimelineEventType.RUN_FINISHED,
    )
    assert tuple(
        event.stage_id
        for event in events
        if event.type is TimelineEventType.STAGE_STARTED
    ) == ("one", "two")


def test_metrics_and_dashboard_reflect_completed_workflow() -> None:
    service, runs, timeline = orchestrator()
    service.execute(
        Workflow(id="workflow", steps=(SimulatedStep("step"),)),
        WorkflowContext(run_id="run"),
    )
    query = RunQueryService(runs, timeline)
    metrics = MetricsService(query)
    client = TestClient(create_app(query, metrics))

    assert metrics.get_summary().successful_runs == 1
    assert metrics.get_summary().duration.count == 1
    assert client.get("/api/v1/runs/run").json()["status"] == "succeeded"
    assert (
        len(client.get("/api/v1/runs/run/timeline").json()["items"])
        == 4
    )


@pytest.mark.parametrize("backend", ["memory", "file", "sqlite"])
def test_integrates_with_every_repository_factory_backend(
    backend: str,
    tmp_path: Path,
) -> None:
    settings = ApplicationSettings(
        storage_backend=backend,
        storage_directory=tmp_path,
        sqlite_database=tmp_path / "asep.db",
    )
    repositories = RepositoryFactory(settings).create()
    service = WorkflowOrchestrator(
        repositories.run_repository,
        repositories.timeline_repository,
        clock=lambda: NOW,
        event_id_generator=id_generator(),
    )

    result = service.execute(
        Workflow(id="workflow", steps=(SimulatedStep("step"),)),
        WorkflowContext(run_id=f"run-{backend}"),
    )

    assert result.status is WorkflowStatus.COMPLETED
    assert (
        repositories.run_repository.get(f"run-{backend}").status
        is RunStatus.SUCCEEDED
    )


def test_result_uses_independent_context_snapshot() -> None:
    service, _, _ = orchestrator()
    context = WorkflowContext(run_id="run")
    result = service.execute(
        Workflow(id="workflow", steps=(SimulatedStep("step"),)),
        context,
    )

    context.values["order"].append("external")

    assert result.context.values["order"] == ["step"]
