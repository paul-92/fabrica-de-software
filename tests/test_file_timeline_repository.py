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
from asep.runs import InMemoryRunRepository, Run
from asep.timeline import (
    FileTimelineRepository,
    InvalidTimelineStorageFormatError,
    TimelineEvent,
    TimelineEventType,
    TimelineRecorder,
    TimelineRepository,
    TimelineStorageReadError,
    TimelineStorageWriteError,
)
from asep.timeline.file_repository import TIMELINE_STORAGE_VERSION
from asep.timeline.serialization import TimelineEventCodec

NOW = datetime(2026, 7, 29, 17, 30, tzinfo=UTC)


def event(
    event_id: str = "event-1",
    *,
    run_id: str = "run-1",
    timestamp: datetime = NOW,
    event_type: TimelineEventType = TimelineEventType.STAGE_STARTED,
    stage_id: str | None = "implementation",
    message: str | None = "Etapa iniciada.",
    metadata=None,
) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        run_id=run_id,
        timestamp=timestamp,
        type=event_type,
        stage_id=stage_id,
        message=message,
        metadata=metadata or {},
    )


def write_document(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": TIMELINE_STORAGE_VERSION,
                "events": events,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def valid_record(**changes) -> dict:
    record = TimelineEventCodec.encode(event())
    record.update(changes)
    return record


def test_constructs_with_path_without_creating_files(tmp_path: Path) -> None:
    target = tmp_path / "deep/storage/timeline-events.json"

    repository = FileTimelineRepository(target)

    assert isinstance(repository, TimelineRepository)
    assert not target.exists()
    assert not target.parent.exists()


def test_missing_file_is_empty_and_read_does_not_create_it(
    tmp_path: Path,
) -> None:
    target = tmp_path / "timeline-events.json"
    repository = FileTimelineRepository(target)

    assert repository.list_by_run("run") == ()
    assert not target.exists()


def test_first_append_creates_parent_and_versioned_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "deep/storage/timeline-events.json"
    repository = FileTimelineRepository(target)

    repository.append(event())

    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["version"] == "1.0"
    assert len(document["events"]) == 1


def test_event_persists_after_new_repository_instance(
    tmp_path: Path,
) -> None:
    target = tmp_path / "timeline-events.json"
    source = event(
        metadata={
            "unicode": "ação",
            "nested": {"items": [1, True, None]},
        }
    )
    FileTimelineRepository(target).append(source)

    restored = FileTimelineRepository(target).list_by_run("run-1")

    assert restored == (source,)
    assert restored[0] is not source
    assert restored[0].type is TimelineEventType.STAGE_STARTED
    assert restored[0].metadata["unicode"] == "ação"


def test_multiple_instances_observe_sequential_writes(
    tmp_path: Path,
) -> None:
    target = tmp_path / "timeline-events.json"
    first = FileTimelineRepository(target)
    second = FileTimelineRepository(target)

    first.append(event("first", run_id="a"))
    second.append(event("second", run_id="b"))

    assert first.list_by_run("a")[0].id == "first"
    assert first.list_by_run("b")[0].id == "second"


def test_timezone_offset_and_utc_are_preserved(tmp_path: Path) -> None:
    target = tmp_path / "timeline-events.json"
    repository = FileTimelineRepository(target)
    offset = timezone(timedelta(hours=-3))
    repository.append(event("utc"))
    repository.append(
        event(
            "offset",
            timestamp=datetime(2026, 7, 29, 14, 30, tzinfo=offset),
        )
    )

    restored = repository.list_by_run("run-1")
    by_id = {item.id: item for item in restored}

    assert by_id["utc"].timestamp.utcoffset() == timedelta(0)
    assert by_id["offset"].timestamp.utcoffset() == timedelta(hours=-3)


def test_optional_fields_and_empty_metadata_round_trip(
    tmp_path: Path,
) -> None:
    target = tmp_path / "timeline-events.json"
    source = event(stage_id=None, message=None, metadata={})

    FileTimelineRepository(target).append(source)

    assert FileTimelineRepository(target).list_by_run("run-1") == (
        source,
    )


def test_json_is_deterministic_and_unicode_is_not_escaped(
    tmp_path: Path,
) -> None:
    target = tmp_path / "timeline-events.json"
    repository = FileTimelineRepository(target)
    repository.append(event(message="ação"))
    first = target.read_bytes()

    repository.append(event("event-2", message="órgão"))
    second = target.read_text(encoding="utf-8")

    assert b'"version": "1.0"' in first
    assert "ação" in second
    assert "\\u00e7" not in second
    assert second.endswith("\n")


def test_codec_is_explicit_and_round_trips() -> None:
    source = event(metadata={"nested": {"ok": True}})

    encoded = TimelineEventCodec.encode(source)
    decoded = TimelineEventCodec.decode(encoded)

    assert tuple(encoded) == (
        "id",
        "run_id",
        "timestamp",
        "type",
        "stage_id",
        "message",
        "metadata",
    )
    assert decoded == source


@pytest.mark.parametrize(
    "content",
    [
        "",
        "  \n",
        "{",
        "null",
        "[]",
        "{}",
        '{"version": "1.0"}',
        '{"events": []}',
        '{"version": "2.0", "events": []}',
        '{"version": "1.0", "events": {}}',
        '{"version": "1.0", "events": [1]}',
        '{"version": "1.0", "events": [], "extra": true}',
        '{"version": "1.0", "events": [], "number": NaN}',
    ],
)
def test_invalid_document_is_explicit_and_not_overwritten(
    tmp_path: Path,
    content: str,
) -> None:
    target = tmp_path / "timeline-events.json"
    target.write_text(content, encoding="utf-8")
    before = target.read_bytes()
    repository = FileTimelineRepository(target)

    with pytest.raises(InvalidTimelineStorageFormatError):
        repository.list_by_run("run")

    assert target.read_bytes() == before


@pytest.mark.parametrize(
    "record",
    [
        {},
        valid_record(id=""),
        valid_record(run_id=""),
        valid_record(timestamp="invalid"),
        valid_record(type="unknown.event"),
        valid_record(metadata={"bad": float("nan")}),
        {**valid_record(), "extra": True},
    ],
)
def test_invalid_event_record_is_rejected(
    tmp_path: Path,
    record: dict,
) -> None:
    target = tmp_path / "timeline-events.json"
    write_document(target, [record])

    with pytest.raises(InvalidTimelineStorageFormatError):
        FileTimelineRepository(target).list_by_run("run-1")


def test_duplicate_ids_already_in_file_are_corruption(
    tmp_path: Path,
) -> None:
    target = tmp_path / "timeline-events.json"
    write_document(target, [valid_record(), valid_record()])

    with pytest.raises(
        InvalidTimelineStorageFormatError,
        match="duplicados",
    ):
        FileTimelineRepository(target).list_by_run("run-1")


def test_read_os_error_is_wrapped_with_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "timeline-events.json"
    repository = FileTimelineRepository(target)
    failure = PermissionError("secret operating system detail")

    def fail_read(*args, **kwargs):
        raise failure

    monkeypatch.setattr(Path, "read_text", fail_read)

    with pytest.raises(TimelineStorageReadError) as captured:
        repository.list_by_run("run")

    assert captured.value.__cause__ is failure
    assert "secret operating system detail" not in str(captured.value)


def test_atomic_replace_uses_short_temp_in_target_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "deep" / "timeline-events.json"
    observed: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def observe_replace(source, destination):
        observed.append((Path(source), Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", observe_replace)

    FileTimelineRepository(target).append(event())

    temporary, destination = observed[0]
    assert temporary.parent == target.parent
    assert destination == target
    assert temporary.name.startswith(".asep-timeline-")
    assert "timeline-events.json" not in temporary.name
    assert not temporary.exists()


def test_failed_replace_preserves_previous_file_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "timeline-events.json"
    repository = FileTimelineRepository(target)
    repository.append(event("first"))
    before = target.read_bytes()
    failure = OSError("replace failed")

    def fail_replace(source, destination):
        raise failure

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(TimelineStorageWriteError) as captured:
        repository.append(event("second"))

    assert captured.value.__cause__ is failure
    assert target.read_bytes() == before
    assert list(tmp_path.glob(".asep-timeline-*.tmp")) == []


def test_directory_creation_failure_is_write_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "blocked/timeline-events.json"
    failure = PermissionError("denied")

    def fail_mkdir(*args, **kwargs):
        raise failure

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)

    with pytest.raises(TimelineStorageWriteError) as captured:
        FileTimelineRepository(target).append(event())

    assert captured.value.__cause__ is failure


def test_append_does_not_modify_source_or_metadata(tmp_path: Path) -> None:
    target = tmp_path / "timeline-events.json"
    source = event(metadata={"nested": {"items": [1, 2]}})
    before = source.model_dump(mode="json")

    FileTimelineRepository(target).append(source)

    assert source.model_dump(mode="json") == before


def test_timeline_recorder_works_without_changes(tmp_path: Path) -> None:
    target = tmp_path / "timeline-events.json"
    repository = FileTimelineRepository(target)
    recorder = TimelineRecorder(
        repository,
        clock=lambda: NOW,
        id_generator=lambda: "recorded",
    )

    recorded = recorder.record(
        "run",
        TimelineEventType.PROVIDER_STARTED,
        message="Provider iniciado.",
    )

    assert FileTimelineRepository(target).list_by_run("run") == (
        recorded,
    )


def test_run_query_reads_persisted_timeline_after_restart(
    tmp_path: Path,
) -> None:
    target = tmp_path / "timeline-events.json"
    recorder = TimelineRecorder(
        FileTimelineRepository(target),
        clock=lambda: NOW,
        id_generator=lambda: "persisted",
    )
    recorder.record("run", TimelineEventType.RUN_STARTED)
    runs = InMemoryRunRepository()
    runs.save(Run(id="run", started_at=NOW))
    query = RunQueryService(runs, FileTimelineRepository(target))

    assert query.get_timeline("run")[0].id == "persisted"


def test_dashboard_api_reads_persisted_timeline(tmp_path: Path) -> None:
    target = tmp_path / "timeline-events.json"
    FileTimelineRepository(target).append(event(run_id="run"))
    runs = InMemoryRunRepository()
    runs.save(Run(id="run", started_at=NOW))
    query = RunQueryService(runs, FileTimelineRepository(target))
    app = create_app(query, MetricsService(query))

    response = TestClient(app).get("/api/v1/runs/run/timeline")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "event-1"


def test_file_repository_has_no_forbidden_dependencies() -> None:
    import asep.timeline.file_repository as repository
    import asep.timeline.serialization as serialization

    source = inspect.getsource(repository) + inspect.getsource(serialization)
    for forbidden in (
        "asep.runs",
        "asep.api",
        "fastapi",
        "asep.cli",
        "asep.metrics",
        "asep.providers",
        "asep.execution_graph",
    ):
        assert forbidden not in source
