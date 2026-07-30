from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.configuration import ApplicationSettings, Configuration, StorageBackend
from asep.repositories import RepositoryFactory
from asep.runs import InMemoryRunRepository
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEvent,
    TimelineEventType,
)
from asep.workflow import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowOrchestrator,
    WorkflowStatus,
)
from asep.workflow_persistence import (
    FileWorkflowRepository,
    InMemoryWorkflowRepository,
    SQLiteWorkflowRepository,
    WorkflowPersistenceService,
    WorkflowRepository,
    WorkflowSnapshot,
    WorkflowSnapshotAlreadyExistsError,
    WorkflowSnapshotNotFoundError,
)
from asep.workflow_persistence.serialization import WorkflowSnapshotCodec

NOW = datetime(2026, 7, 30, 21, 0, tzinfo=UTC)


def snapshot(
    *,
    snapshot_id: str = "snapshot-1",
    workflow_id: str = "workflow",
    run_id: str = "run-1",
    status: WorkflowStatus = WorkflowStatus.COMPLETED,
    started_at: datetime = NOW,
) -> WorkflowSnapshot:
    return WorkflowSnapshot(
        id=snapshot_id,
        workflow_id=workflow_id,
        run_id=run_id,
        workflow_version="1.0",
        name="Workflow",
        description="Persisted workflow",
        status=status,
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=2),
        duration_seconds=2,
        executed_steps=("one",),
        pending_steps=("two",),
        agent_id="reviewer",
        timeline_event_ids=("event-1",),
        metrics={"completed_steps": 1},
        metadata={"classification": "internal"},
        created_at=started_at + timedelta(seconds=3),
    )


def repositories(
    tmp_path: Path,
) -> tuple[WorkflowRepository, ...]:
    return (
        InMemoryWorkflowRepository(),
        FileWorkflowRepository(tmp_path / "workflows.json"),
        SQLiteWorkflowRepository(tmp_path / "workflows.db"),
    )


def test_snapshot_is_strict_immutable_serializable_and_equal() -> None:
    source = snapshot()
    encoded = WorkflowSnapshotCodec.encode(source)
    decoded = WorkflowSnapshotCodec.decode(encoded)

    assert decoded == source
    assert encoded["status"] == "completed"
    assert encoded["metrics"] == {"completed_steps": 1}
    with pytest.raises(ValidationError):
        source.name = "Changed"
    with pytest.raises(ValidationError):
        WorkflowSnapshot.model_validate(
            {**encoded, "unexpected": True}
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"id": ""},
        {"finished_at": NOW - timedelta(seconds=1)},
        {"duration_seconds": -1},
        {"pending_steps": ("one",)},
        {"started_at": NOW.replace(tzinfo=None)},
        {"metadata": {"secret": object()}},
    ],
)
def test_snapshot_rejects_invalid_state(changes: dict[str, object]) -> None:
    with pytest.raises((ValidationError, TypeError, ValueError)):
        snapshot().model_copy(update=changes).model_dump()
        WorkflowSnapshot.model_validate(
            {**snapshot().model_dump(), **changes}
        )


@pytest.mark.parametrize("repository_index", range(3))
def test_repository_contract_crud_queries_and_history(
    repository_index: int,
    tmp_path: Path,
) -> None:
    repository = repositories(tmp_path)[repository_index]
    first = snapshot()
    second = snapshot(
        snapshot_id="snapshot-2",
        workflow_id="workflow",
        run_id="run-2",
        status=WorkflowStatus.FAILED,
        started_at=NOW + timedelta(minutes=1),
    )
    third = snapshot(
        snapshot_id="snapshot-3",
        workflow_id="other",
        run_id="run-1",
        started_at=NOW + timedelta(minutes=2),
    )

    repository.save(second)
    repository.save(first)
    repository.save(third)

    assert repository.exists(first.id)
    assert repository.get(first.id) == first
    assert tuple(item.id for item in repository.list()) == (
        "snapshot-1",
        "snapshot-2",
        "snapshot-3",
    )
    assert repository.find_by_status(WorkflowStatus.FAILED) == (second,)
    assert repository.find_by_run("run-1") == (first, third)
    assert repository.find_by_workflow("workflow") == (first, second)
    assert repository.find_by_period(
        NOW + timedelta(seconds=30),
        NOW + timedelta(minutes=1, seconds=30),
    ) == (second,)
    assert repository.find_by_run("missing") == ()

    changed = first.model_copy(
        update={"metadata": {"classification": "public"}}
    )
    repository.update(changed)
    assert repository.get(first.id).metadata == {
        "classification": "public"
    }
    assert len(repository.find_by_workflow("workflow")) == 2

    with pytest.raises(WorkflowSnapshotAlreadyExistsError):
        repository.save(first)
    with pytest.raises(WorkflowSnapshotNotFoundError):
        repository.get("missing")
    with pytest.raises(WorkflowSnapshotNotFoundError):
        repository.update(
            snapshot(snapshot_id="missing")
        )
    with pytest.raises(ValueError, match="período"):
        repository.find_by_period(NOW, NOW - timedelta(seconds=1))


def test_file_and_sqlite_persist_between_instances(tmp_path: Path) -> None:
    file_path = tmp_path / "workflows.json"
    database_path = tmp_path / "workflows.db"
    FileWorkflowRepository(file_path).save(snapshot())
    SQLiteWorkflowRepository(database_path).save(snapshot())

    assert FileWorkflowRepository(file_path).get("snapshot-1") == snapshot()
    assert (
        SQLiteWorkflowRepository(database_path).get("snapshot-1")
        == snapshot()
    )


@dataclass
class Step:
    id: str

    def execute(self, context: WorkflowContext) -> None:
        context.values["last"] = self.id


def execution_result() -> WorkflowExecutionResult:
    return WorkflowExecutionResult(
        run_id="run-1",
        workflow_id="workflow",
        status=WorkflowStatus.COMPLETED,
        started_at=NOW,
        finished_at=NOW + timedelta(seconds=2),
        completed_steps=("one",),
        context=WorkflowContext(run_id="run-1"),
        timeline=(
            TimelineEvent(
                id="event-1",
                run_id="run-1",
                timestamp=NOW,
                type=TimelineEventType.STAGE_FINISHED,
            ),
        ),
        metrics={"completed_steps": 1},
    )


def definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="workflow",
        name="Workflow",
        description="Definition",
        metadata={"version": "2.0", "owner": "platform"},
        steps=(Step("one"), Step("two")),
    )


def test_service_creates_and_persists_detached_snapshot() -> None:
    repository = InMemoryWorkflowRepository()
    service = WorkflowPersistenceService(
        repository,
        clock=lambda: NOW + timedelta(seconds=3),
        id_generator=lambda: "snapshot-1",
    )

    persisted = service.persist(
        definition(),
        execution_result(),
        agent_id="reviewer",
        metadata={"source": "orchestrator"},
    )

    assert persisted.workflow_version == "2.0"
    assert persisted.executed_steps == ("one",)
    assert persisted.pending_steps == ("two",)
    assert persisted.timeline_event_ids == ("event-1",)
    assert persisted.agent_id == "reviewer"
    assert service.get("snapshot-1") == persisted
    assert service.list() == (persisted,)


def test_service_rejects_mismatched_definition_and_result() -> None:
    service = WorkflowPersistenceService(InMemoryWorkflowRepository())

    with pytest.raises(ValueError, match="diverge"):
        service.create_snapshot(
            WorkflowDefinition(id="other", steps=(Step("one"),)),
            execution_result(),
        )


@pytest.mark.parametrize("backend", list(StorageBackend))
def test_factory_supplies_workflow_repository_for_every_backend(
    backend: StorageBackend,
    tmp_path: Path,
) -> None:
    settings = ApplicationSettings(
        storage_backend=backend,
        storage_directory=tmp_path / "storage",
        sqlite_database=tmp_path / "asep.db",
    )

    bundle = RepositoryFactory(settings).create()

    assert isinstance(bundle.workflow_repository, WorkflowRepository)
    bundle.workflow_repository.save(snapshot())
    assert bundle.workflow_repository.get("snapshot-1") == snapshot()


def test_configuration_supports_custom_workflow_filename() -> None:
    settings = Configuration.load(
        {"ASEP_WORKFLOWS_FILENAME": "custom-workflows.json"}
    )

    assert settings.workflows_filename == "custom-workflows.json"
    with pytest.raises(ValidationError):
        WorkflowSnapshot.model_validate({})


def test_orchestrator_persists_terminal_result_via_injected_service() -> None:
    workflow_repository = InMemoryWorkflowRepository()
    service = WorkflowPersistenceService(
        workflow_repository,
        clock=lambda: NOW + timedelta(seconds=5),
        id_generator=lambda: "snapshot-1",
    )
    counter = 0

    def event_id() -> str:
        nonlocal counter
        counter += 1
        return f"event-{counter}"

    orchestrator = WorkflowOrchestrator(
        InMemoryRunRepository(),
        InMemoryTimelineRepository(),
        clock=lambda: NOW,
        event_id_generator=event_id,
        workflow_persistence=service,
    )

    result = orchestrator.execute(
        WorkflowDefinition(
            id="workflow",
            metadata={"version": "1.0"},
            steps=(Step("one"),),
        ),
        WorkflowContext(run_id="run-1"),
    )

    persisted = workflow_repository.get("snapshot-1")
    assert result.status is WorkflowStatus.COMPLETED
    assert persisted.status is WorkflowStatus.COMPLETED
    assert persisted.timeline_event_ids == tuple(
        event.id for event in result.timeline
    )
    assert persisted.metrics == result.metrics
