from __future__ import annotations

import inspect
import json
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asep.api import create_app
from asep.application import RunQueryService
from asep.metrics import MetricsService
from asep.runs import (
    FileRunRepository,
    InvalidRunStorageFormatError,
    Run,
    RunError,
    RunRepository,
    RunStatus,
    RunStorageReadError,
    RunStorageWriteError,
)
from asep.runs.file_repository import RUN_STORAGE_VERSION
from asep.runs.serialization import RunCodec
from asep.timeline import InMemoryTimelineRepository

START = datetime(2026, 7, 30, 10, 0, tzinfo=UTC)


def run(
    run_id: str = "run-1",
    *,
    status: RunStatus = RunStatus.PENDING,
    started_at: datetime = START,
    finished_at: datetime | None = None,
    metadata=None,
    **values,
) -> Run:
    return Run(
        id=run_id,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        metadata=metadata or {},
        **values,
    )


def write_document(path: Path, runs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"version": RUN_STORAGE_VERSION, "runs": runs},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def valid_record(**changes) -> dict:
    record = RunCodec.encode(run())
    record.update(changes)
    return record


def test_constructor_creates_parent_and_empty_file(tmp_path: Path) -> None:
    target = tmp_path / "deep/storage/runs.json"

    repository = FileRunRepository(target)

    assert isinstance(repository, RunRepository)
    assert repository.list() == ()
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "runs": [],
        "version": "1.0",
    }


def test_empty_existing_file_is_empty_collection(tmp_path: Path) -> None:
    target = tmp_path / "runs.json"
    target.write_text("", encoding="utf-8")

    repository = FileRunRepository(target)

    assert repository.list() == ()
    assert target.read_text(encoding="utf-8") == ""


def test_save_and_restart_preserve_complete_run(tmp_path: Path) -> None:
    target = tmp_path / "runs.json"
    offset = timezone(timedelta(hours=-3))
    source = run(
        status=RunStatus.FAILED,
        started_at=datetime(2026, 7, 30, 7, 0, tzinfo=offset),
        finished_at=datetime(2026, 7, 30, 7, 2, tzinfo=offset),
        project_id="projeto-ação",
        workflow_id="software-project",
        stage_id="análise",
        provider_name="códex",
        summary="Falha controlada.",
        error=RunError(
            type="ProviderError",
            message="Indisponível.",
            details={"retryable": False, "attempt": 2},
        ),
        metadata={
            "unicode": "órgão",
            "nested": {"items": [1, True, None]},
        },
    )
    FileRunRepository(target).save(source)

    restored = FileRunRepository(target).get("run-1")

    assert restored == source
    assert restored is not source
    assert restored.status is RunStatus.FAILED
    assert restored.started_at.utcoffset() == timedelta(hours=-3)
    assert restored.finished_at is not None
    assert restored.finished_at - restored.started_at == timedelta(minutes=2)
    assert restored.metadata["unicode"] == "órgão"


def test_save_same_id_updates_persisted_snapshot(tmp_path: Path) -> None:
    target = tmp_path / "runs.json"
    repository = FileRunRepository(target)
    repository.save(run(status=RunStatus.RUNNING))
    updated = run(
        status=RunStatus.SUCCEEDED,
        finished_at=START + timedelta(seconds=3),
        summary="Done.",
    )

    repository.save(updated)

    assert FileRunRepository(target).list() == (updated,)


def test_multiple_runs_are_persisted_deterministically(
    tmp_path: Path,
) -> None:
    target = tmp_path / "runs.json"
    repository = FileRunRepository(target)
    repository.save(run("z"))
    repository.save(run("old", started_at=START - timedelta(seconds=1)))
    repository.save(run("a"))

    restored = FileRunRepository(target).list()
    document = json.loads(target.read_text(encoding="utf-8"))

    assert tuple(item.id for item in restored) == ("old", "a", "z")
    assert [item["id"] for item in document["runs"]] == [
        "old",
        "a",
        "z",
    ]


def test_json_is_stable_readable_and_unicode_is_not_escaped(
    tmp_path: Path,
) -> None:
    target = tmp_path / "runs.json"
    repository = FileRunRepository(target)
    repository.save(run(project_id="ação"))
    content = target.read_text(encoding="utf-8")

    assert content.endswith("\n")
    assert '"version": "1.0"' in content
    assert "ação" in content
    assert "\\u00e7" not in content


def test_codec_explicitly_round_trips_every_field() -> None:
    source = run(
        provider_name="codex",
        stage_id="analysis",
        metadata={"nested": {"value": 1}},
    )

    encoded = RunCodec.encode(source)
    decoded = RunCodec.decode(encoded)

    assert tuple(encoded) == (
        "id",
        "status",
        "started_at",
        "finished_at",
        "project_id",
        "workflow_id",
        "stage_id",
        "provider_name",
        "summary",
        "error",
        "metadata",
    )
    assert decoded == source


@pytest.mark.parametrize(
    "content",
    [
        "{",
        "null",
        "[]",
        "{}",
        '{"version": "1.0"}',
        '{"runs": []}',
        '{"version": "2.0", "runs": []}',
        '{"version": "1.0", "runs": {}}',
        '{"version": "1.0", "runs": [1]}',
        '{"version": "1.0", "runs": [], "extra": true}',
        '{"version": "1.0", "runs": [], "number": NaN}',
    ],
)
def test_invalid_document_fails_during_initialization_without_overwrite(
    tmp_path: Path,
    content: str,
) -> None:
    target = tmp_path / "runs.json"
    target.write_text(content, encoding="utf-8")
    before = target.read_bytes()

    with pytest.raises(InvalidRunStorageFormatError):
        FileRunRepository(target)

    assert target.read_bytes() == before


@pytest.mark.parametrize(
    "record",
    [
        {},
        valid_record(id=""),
        valid_record(status="unknown"),
        valid_record(started_at="invalid"),
        valid_record(finished_at="invalid"),
        valid_record(metadata={"bad": float("nan")}),
        {**valid_record(), "extra": True},
    ],
)
def test_invalid_run_record_is_rejected(
    tmp_path: Path,
    record: dict,
) -> None:
    target = tmp_path / "runs.json"
    write_document(target, [record])

    with pytest.raises(InvalidRunStorageFormatError):
        FileRunRepository(target)


def test_duplicate_ids_in_file_are_corruption(tmp_path: Path) -> None:
    target = tmp_path / "runs.json"
    write_document(target, [valid_record(), valid_record()])

    with pytest.raises(InvalidRunStorageFormatError, match="duplicados"):
        FileRunRepository(target)


def test_read_error_is_wrapped_and_chained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "runs.json"
    failure = PermissionError("sensitive operating system detail")

    def fail_read(*args, **kwargs):
        raise failure

    monkeypatch.setattr(Path, "read_text", fail_read)

    with pytest.raises(RunStorageReadError) as captured:
        FileRunRepository(target)

    assert captured.value.__cause__ is failure
    assert "sensitive operating system detail" not in str(captured.value)


def test_atomic_replace_uses_short_temp_in_same_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "deep/runs.json"
    observed: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def observe_replace(source, destination):
        observed.append((Path(source), Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", observe_replace)
    repository = FileRunRepository(target)
    repository.save(run())

    assert len(observed) == 2
    for temporary, destination in observed:
        assert temporary.parent == target.parent
        assert destination == target
        assert temporary.name.startswith(".asep-runs-")
        assert "runs.json" not in temporary.name
        assert not temporary.exists()


def test_failed_update_preserves_file_and_in_memory_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "runs.json"
    repository = FileRunRepository(target)
    original = run(status=RunStatus.RUNNING)
    repository.save(original)
    before = target.read_bytes()
    failure = OSError("replace failed")

    def fail_replace(source, destination):
        raise failure

    monkeypatch.setattr(os, "replace", fail_replace)
    updated = run(
        status=RunStatus.SUCCEEDED,
        finished_at=START + timedelta(seconds=1),
    )

    with pytest.raises(RunStorageWriteError) as captured:
        repository.save(updated)

    assert captured.value.__cause__ is failure
    assert repository.get("run-1") == original
    assert target.read_bytes() == before
    assert list(tmp_path.glob(".asep-runs-*.tmp")) == []


def test_initial_directory_creation_failure_is_write_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "blocked/runs.json"
    failure = PermissionError("denied")

    def fail_mkdir(*args, **kwargs):
        raise failure

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)

    with pytest.raises(RunStorageWriteError) as captured:
        FileRunRepository(target)

    assert captured.value.__cause__ is failure


def test_save_does_not_modify_source_or_metadata(tmp_path: Path) -> None:
    source = run(metadata={"nested": {"items": [1, 2]}})
    before = source.model_dump(mode="json")

    FileRunRepository(tmp_path / "runs.json").save(source)

    assert source.model_dump(mode="json") == before


def test_run_query_and_metrics_work_after_restart(tmp_path: Path) -> None:
    target = tmp_path / "runs.json"
    repository = FileRunRepository(target)
    repository.save(
        run(
            "success",
            status=RunStatus.SUCCEEDED,
            finished_at=START + timedelta(seconds=2),
        )
    )
    query = RunQueryService(
        FileRunRepository(target),
        InMemoryTimelineRepository(),
    )

    assert query.get_run("success").status is RunStatus.SUCCEEDED
    assert MetricsService(query).get_summary().success_rate == 1


def test_dashboard_api_reads_persisted_runs(tmp_path: Path) -> None:
    target = tmp_path / "runs.json"
    FileRunRepository(target).save(run("persisted"))
    query = RunQueryService(
        FileRunRepository(target),
        InMemoryTimelineRepository(),
    )
    app = create_app(query, MetricsService(query))

    response = TestClient(app).get("/api/v1/runs")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "persisted"


def test_file_repository_has_no_forbidden_dependencies() -> None:
    import asep.runs.file_repository as repository
    import asep.runs.serialization as serialization

    source = inspect.getsource(repository) + inspect.getsource(serialization)
    for forbidden in (
        "asep.timeline",
        "asep.api",
        "fastapi",
        "asep.cli",
        "asep.metrics",
        "asep.providers",
        "asep.execution_graph",
    ):
        assert forbidden not in source
