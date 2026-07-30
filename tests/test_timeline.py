from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from asep.timeline import (
    DuplicateTimelineEventError,
    InMemoryTimelineRepository,
    TimelineEvent,
    TimelineEventType,
    TimelineRecorder,
    TimelineRepository,
)

NOW = datetime(2026, 7, 29, 15, 0, tzinfo=UTC)


def event(
    event_id: str = "event-1",
    *,
    run_id: str = "run-1",
    timestamp: datetime = NOW,
    event_type: TimelineEventType = TimelineEventType.RUN_STARTED,
    **values,
) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        run_id=run_id,
        timestamp=timestamp,
        type=event_type,
        **values,
    )


def test_creates_timeline_event_with_all_public_fields() -> None:
    source = event(
        event_type=TimelineEventType.STAGE_STARTED,
        stage_id="analysis",
        message="Stage started.",
        metadata={"attempt": 1},
    )

    assert source.id == "event-1"
    assert source.run_id == "run-1"
    assert source.timestamp == NOW
    assert source.type is TimelineEventType.STAGE_STARTED
    assert source.stage_id == "analysis"
    assert source.message == "Stage started."
    assert source.metadata["attempt"] == 1


def test_event_defaults_are_safe() -> None:
    source = event()

    assert source.stage_id is None
    assert source.message is None
    assert dict(source.metadata) == {}


@pytest.mark.parametrize(
    ("event_type", "serialized"),
    [
        (TimelineEventType.RUN_STARTED, "run.started"),
        (TimelineEventType.RUN_FINISHED, "run.finished"),
        (TimelineEventType.STAGE_STARTED, "stage.started"),
        (TimelineEventType.STAGE_FINISHED, "stage.finished"),
        (TimelineEventType.PROVIDER_STARTED, "provider.started"),
        (TimelineEventType.PROVIDER_FINISHED, "provider.finished"),
        (TimelineEventType.WARNING, "warning"),
        (TimelineEventType.ERROR, "error"),
    ],
)
def test_event_types_have_stable_serialized_values(
    event_type: TimelineEventType,
    serialized: str,
) -> None:
    assert event_type.value == serialized


def test_append_and_list_event() -> None:
    repository = InMemoryTimelineRepository()
    source = event()

    repository.append(source)

    assert repository.list_by_run("run-1") == (source,)
    assert repository.list_by_run("run-1")[0] is not source


def test_list_for_run_without_events_is_empty() -> None:
    assert InMemoryTimelineRepository().list_by_run("run-1") == ()


def test_events_are_separated_by_run_id() -> None:
    repository = InMemoryTimelineRepository()
    repository.append(event("a", run_id="run-a"))
    repository.append(event("b", run_id="run-b"))

    assert tuple(
        item.id for item in repository.list_by_run("run-a")
    ) == ("a",)
    assert tuple(
        item.id for item in repository.list_by_run("run-b")
    ) == ("b",)


def test_events_are_ordered_by_timestamp() -> None:
    repository = InMemoryTimelineRepository()
    repository.append(event("last", timestamp=NOW + timedelta(seconds=1)))
    repository.append(event("first", timestamp=NOW))

    assert tuple(
        item.id for item in repository.list_by_run("run-1")
    ) == ("first", "last")


def test_equal_timestamps_are_ordered_by_event_id() -> None:
    repository = InMemoryTimelineRepository()
    repository.append(event("z"))
    repository.append(event("a"))
    repository.append(event("middle"))

    assert tuple(
        item.id for item in repository.list_by_run("run-1")
    ) == ("a", "middle", "z")


def test_duplicate_event_id_is_rejected_globally() -> None:
    repository = InMemoryTimelineRepository()
    repository.append(event("same", run_id="run-a"))

    with pytest.raises(DuplicateTimelineEventError, match="same"):
        repository.append(event("same", run_id="run-b"))


def test_repositories_are_isolated() -> None:
    first = InMemoryTimelineRepository()
    second = InMemoryTimelineRepository()
    first.append(event())

    assert len(first.list_by_run("run-1")) == 1
    assert second.list_by_run("run-1") == ()


def test_repository_does_not_expose_internal_collection() -> None:
    repository = InMemoryTimelineRepository()
    repository.append(event())

    first = repository.list_by_run("run-1")
    second = repository.list_by_run("run-1")

    assert isinstance(first, tuple)
    assert first is not second
    assert first[0] is not second[0]


def test_event_and_nested_metadata_are_immutable() -> None:
    source = event(
        metadata={"nested": {"ok": True}, "items": [1, 2]}
    )

    with pytest.raises(ValidationError):
        source.message = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        source.metadata["new"] = True  # type: ignore[index]
    with pytest.raises(TypeError):
        source.metadata["nested"]["ok"] = False  # type: ignore[index]
    assert source.metadata["items"] == (1, 2)


def test_metadata_serializes_only_to_json_primitives() -> None:
    source = event(
        metadata={
            "text": "á",
            "number": 2.5,
            "enabled": True,
            "items": [1, None, {"key": "value"}],
        }
    )

    dumped = source.model_dump(mode="json")

    assert dumped["type"] == "run.started"
    assert dumped["timestamp"] == NOW.isoformat().replace("+00:00", "Z")
    assert dumped["metadata"]["items"] == [1, None, {"key": "value"}]
    json.dumps(dumped, allow_nan=False)


@pytest.mark.parametrize(
    "metadata",
    [
        {"bad": object()},
        {"bad": {1: "key"}},
        {"bad": {1, 2}},
        {"bad": float("nan")},
        {"bad": float("inf")},
    ],
)
def test_invalid_metadata_is_rejected(metadata: dict) -> None:
    with pytest.raises(ValidationError, match="metadata"):
        event(metadata=metadata)


@pytest.mark.parametrize(
    "values",
    [
        {"event_id": " "},
        {"run_id": ""},
        {"stage_id": " "},
        {"message": ""},
        {"timestamp": datetime(2026, 7, 29, 15, 0)},
    ],
)
def test_invalid_identity_text_or_timestamp_is_rejected(
    values: dict,
) -> None:
    with pytest.raises(ValidationError):
        event(**values)


def test_empty_run_id_query_is_rejected() -> None:
    with pytest.raises(ValueError, match="run_id"):
        InMemoryTimelineRepository().list_by_run(" ")


def test_recorder_uses_injected_clock_and_id_generator() -> None:
    repository = InMemoryTimelineRepository()
    recorder = TimelineRecorder(
        repository,
        clock=lambda: NOW,
        id_generator=lambda: "generated-id",
    )

    result = recorder.record(
        "run-1",
        TimelineEventType.PROVIDER_STARTED,
        stage_id="analysis",
        message="Provider started.",
    )

    assert result.id == "generated-id"
    assert result.timestamp == NOW
    assert repository.list_by_run("run-1") == (result,)


def test_recorder_returns_event_and_delegates_once() -> None:
    class SpyRepository:
        def __init__(self) -> None:
            self.appended: list[TimelineEvent] = []

        def append(self, item: TimelineEvent) -> None:
            self.appended.append(item)

        def list_by_run(self, run_id: str) -> tuple[TimelineEvent, ...]:
            return tuple(self.appended)

    repository = SpyRepository()
    recorder = TimelineRecorder(
        repository,
        clock=lambda: NOW,
        id_generator=lambda: "id",
    )

    result = recorder.record("run", TimelineEventType.WARNING)

    assert repository.appended == [result]


def test_record_error_stores_neutral_details_without_traceback() -> None:
    repository = InMemoryTimelineRepository()
    recorder = TimelineRecorder(
        repository,
        clock=lambda: NOW,
        id_generator=lambda: "error-id",
    )
    original = RuntimeError("provider unavailable")

    result = recorder.record_error(
        "run-1",
        original,
        stage_id="analysis",
        metadata={"retryable": False},
    )

    assert result.type is TimelineEventType.ERROR
    assert result.message == "provider unavailable"
    assert result.metadata == {
        "retryable": False,
        "exception_type": "RuntimeError",
    }
    assert "traceback" not in result.metadata
    assert original.args == ("provider unavailable",)


def test_recorder_failure_is_propagated_unchanged() -> None:
    failure = DuplicateTimelineEventError("forced")

    class FailingRepository:
        def append(self, item: TimelineEvent) -> None:
            raise failure

        def list_by_run(self, run_id: str) -> tuple[TimelineEvent, ...]:
            return ()

    recorder = TimelineRecorder(
        FailingRepository(),
        clock=lambda: NOW,
        id_generator=lambda: "id",
    )

    with pytest.raises(DuplicateTimelineEventError) as captured:
        recorder.record("run", TimelineEventType.RUN_STARTED)

    assert captured.value is failure


def test_implementation_satisfies_repository_protocol() -> None:
    repository: TimelineRepository = InMemoryTimelineRepository()

    assert isinstance(repository, TimelineRepository)


def test_public_exports_are_intentional() -> None:
    import asep.timeline as timeline

    assert set(timeline.__all__) == {
        "DuplicateTimelineEventError",
        "FileTimelineRepository",
        "InMemoryTimelineRepository",
        "InvalidTimelineStorageFormatError",
        "TimelineEvent",
        "TimelineEventType",
        "TimelineRecorder",
        "TimelineRepository",
        "TimelineStorageError",
        "TimelineStorageReadError",
        "TimelineStorageWriteError",
        "SQLiteTimelineRepository",
    }


def test_timeline_has_no_forbidden_architecture_dependencies() -> None:
    import inspect

    import asep.timeline.in_memory as in_memory
    import asep.timeline.models as models
    import asep.timeline.recorder as recorder
    import asep.timeline.repository as repository

    source = "\n".join(
        inspect.getsource(module)
        for module in (models, repository, in_memory, recorder)
    )
    for forbidden in (
        "asep.providers",
        "asep.execution_graph",
        "asep.exporters",
        "asep.cli",
        "asep.orchestrator",
    ):
        assert forbidden not in source
