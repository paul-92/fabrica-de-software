from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from asep.errors import RunNotFoundError
from asep.runs import (
    InMemoryRunRepository,
    Run,
    RunError,
    RunRepository,
    RunStatus,
)

START = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def make_run(
    run_id: str = "run-1",
    *,
    status: RunStatus = RunStatus.PENDING,
    started_at: datetime = START,
    **values,
) -> Run:
    return Run(
        id=run_id,
        status=status,
        started_at=started_at,
        **values,
    )


def test_creates_run_with_neutral_fields() -> None:
    run = make_run(
        project_id="project",
        workflow_id="workflow",
        stage_id="analysis",
        provider_name="codex",
        summary="Execution accepted.",
    )

    assert run.id == "run-1"
    assert run.project_id == "project"
    assert run.workflow_id == "workflow"
    assert run.stage_id == "analysis"
    assert run.provider_name == "codex"
    assert run.summary == "Execution accepted."


def test_run_defaults_are_safe() -> None:
    run = make_run()

    assert run.status is RunStatus.PENDING
    assert run.finished_at is None
    assert run.project_id is None
    assert run.workflow_id is None
    assert run.stage_id is None
    assert run.provider_name is None
    assert run.summary is None
    assert run.error is None
    assert dict(run.metadata) == {}


@pytest.mark.parametrize(
    ("status", "serialized", "terminal"),
    [
        (RunStatus.PENDING, "pending", False),
        (RunStatus.RUNNING, "running", False),
        (RunStatus.SUCCEEDED, "succeeded", True),
        (RunStatus.FAILED, "failed", True),
        (RunStatus.CANCELLED, "cancelled", True),
    ],
)
def test_run_status_has_stable_value_and_terminal_semantics(
    status: RunStatus,
    serialized: str,
    terminal: bool,
) -> None:
    assert status.value == serialized
    assert status.is_terminal is terminal


def test_save_and_get_run() -> None:
    repository = InMemoryRunRepository()
    source = make_run()

    repository.save(source)

    assert repository.get(source.id) == source
    assert repository.get(source.id) is not source


def test_save_updates_existing_run_with_same_id() -> None:
    repository = InMemoryRunRepository()
    repository.save(make_run(status=RunStatus.RUNNING))
    updated = make_run(
        status=RunStatus.SUCCEEDED,
        finished_at=START + timedelta(minutes=1),
        summary="Done.",
    )

    repository.save(updated)

    assert repository.list() == (updated,)


def test_get_missing_run_raises_existing_domain_error() -> None:
    repository = InMemoryRunRepository()

    with pytest.raises(RunNotFoundError, match="missing"):
        repository.get("missing")


def test_list_empty_repository() -> None:
    assert InMemoryRunRepository().list() == ()


def test_list_is_deterministic_by_started_at_then_id() -> None:
    repository = InMemoryRunRepository()
    repository.save(make_run("z", started_at=START))
    repository.save(
        make_run("first", started_at=START - timedelta(minutes=1))
    )
    repository.save(make_run("a", started_at=START))

    assert tuple(run.id for run in repository.list()) == (
        "first",
        "a",
        "z",
    )


def test_repository_instances_are_isolated() -> None:
    first = InMemoryRunRepository()
    second = InMemoryRunRepository()
    first.save(make_run())

    assert len(first.list()) == 1
    assert second.list() == ()


def test_list_does_not_expose_internal_collection() -> None:
    repository = InMemoryRunRepository()
    repository.save(make_run())

    listed = repository.list()

    assert isinstance(listed, tuple)
    assert listed is not repository.list()


def test_run_and_nested_metadata_are_immutable() -> None:
    run = make_run(
        metadata={
            "nested": {"enabled": True},
            "items": [1, 2],
        }
    )

    with pytest.raises(ValidationError):
        run.status = RunStatus.FAILED  # type: ignore[misc]
    with pytest.raises(TypeError):
        run.metadata["new"] = True  # type: ignore[index]
    with pytest.raises(TypeError):
        run.metadata["nested"]["enabled"] = False  # type: ignore[index]
    assert run.metadata["items"] == (1, 2)


def test_get_returns_independent_deep_snapshot() -> None:
    repository = InMemoryRunRepository()
    repository.save(make_run(metadata={"nested": {"count": 1}}))

    first = repository.get("run-1")
    second = repository.get("run-1")

    assert first is not second
    assert first.metadata is not second.metadata
    assert first.metadata["nested"] is not second.metadata["nested"]


def test_metadata_accepts_only_json_values_and_serializes_to_primitives() -> None:
    run = make_run(
        metadata={
            "text": "á",
            "number": 3.5,
            "enabled": True,
            "items": [1, None, {"key": "value"}],
        }
    )

    dumped = run.model_dump(mode="json")

    assert json.loads(json.dumps(dumped, allow_nan=False)) == dumped
    assert dumped["status"] == "pending"
    assert dumped["started_at"] == START.isoformat().replace("+00:00", "Z")
    assert dumped["metadata"]["items"] == [1, None, {"key": "value"}]


@pytest.mark.parametrize(
    "metadata",
    [
        {"bad": object()},
        {"bad": {1: "non-string key"}},
        {"bad": {1, 2}},
        {"bad": float("nan")},
        {"bad": float("inf")},
    ],
)
def test_rejects_non_serializable_metadata(metadata: dict) -> None:
    with pytest.raises(ValidationError, match="metadata"):
        make_run(metadata=metadata)


def test_error_is_neutral_immutable_and_serializable() -> None:
    error = RunError(
        type="ProviderExecutionError",
        message="Provider failed.",
        details={"exit_code": 2, "retryable": False},
    )
    run = make_run(status=RunStatus.FAILED, error=error)

    dumped = run.model_dump(mode="json")

    assert dumped["error"] == {
        "type": "ProviderExecutionError",
        "message": "Provider failed.",
        "details": {"exit_code": 2, "retryable": False},
    }
    json.dumps(dumped, allow_nan=False)


def test_timestamps_must_be_aware_and_ordered() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        make_run(started_at=datetime(2026, 7, 29, 12, 0))
    with pytest.raises(ValidationError, match="preceder"):
        make_run(finished_at=START - timedelta(seconds=1))


def test_in_memory_implementation_satisfies_repository_protocol() -> None:
    repository: RunRepository = InMemoryRunRepository()

    assert isinstance(repository, RunRepository)


def test_public_exports_are_intentional() -> None:
    import asep.runs as runs

    assert set(runs.__all__) == {
        "FileRunRepository",
        "InMemoryRunRepository",
        "InvalidRunStorageFormatError",
        "Run",
        "RunError",
        "RunRepository",
        "RunStatus",
        "RunStorageError",
        "RunStorageReadError",
        "RunStorageWriteError",
        "SQLiteRunRepository",
    }
