from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from asep.timeline import (
    DuplicateTimelineEventError,
    FileTimelineRepository,
    InMemoryTimelineRepository,
    TimelineEvent,
    TimelineEventType,
    TimelineRepository,
    SQLiteTimelineRepository,
)

NOW = datetime(2026, 7, 29, 17, 0, tzinfo=UTC)


def event(
    event_id: str,
    *,
    run_id: str = "run",
    timestamp: datetime = NOW,
    message: str | None = None,
) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        run_id=run_id,
        timestamp=timestamp,
        type=TimelineEventType.RUN_STARTED,
        message=message,
    )


@pytest.fixture(params=["memory", "file", "sqlite"])
def repository(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> TimelineRepository:
    factories: dict[str, Callable[[], TimelineRepository]] = {
        "memory": InMemoryTimelineRepository,
        "file": lambda: FileTimelineRepository(
            tmp_path / "timeline-events.json"
        ),
        "sqlite": lambda: SQLiteTimelineRepository(
            tmp_path / "asep.db"
        ),
    }
    return factories[request.param]()


def test_contract_starts_empty(repository: TimelineRepository) -> None:
    assert repository.list_by_run("run") == ()


def test_contract_appends_and_returns_snapshot(
    repository: TimelineRepository,
) -> None:
    source = event("event")

    repository.append(source)
    stored = repository.list_by_run("run")

    assert stored == (source,)
    assert stored[0] is not source


def test_contract_separates_runs(repository: TimelineRepository) -> None:
    repository.append(event("a", run_id="run-a"))
    repository.append(event("b", run_id="run-b"))

    assert tuple(
        item.id for item in repository.list_by_run("run-a")
    ) == ("a",)
    assert tuple(
        item.id for item in repository.list_by_run("run-b")
    ) == ("b",)


def test_contract_orders_distinct_timestamps_chronologically(
    repository: TimelineRepository,
) -> None:
    repository.append(
        event("second", timestamp=NOW + timedelta(seconds=1))
    )
    repository.append(event("first"))

    assert tuple(
        item.id for item in repository.list_by_run("run")
    ) == ("first", "second")


def test_contract_preserves_insertion_order_for_equal_timestamps(
    repository: TimelineRepository,
) -> None:
    repository.append(event("z"))
    repository.append(event("a"))
    repository.append(event("middle"))

    assert tuple(
        item.id for item in repository.list_by_run("run")
    ) == ("z", "a", "middle")


def test_contract_equal_timestamps_remain_isolated_by_run(
    repository: TimelineRepository,
) -> None:
    repository.append(event("run-a-first", run_id="run-a"))
    repository.append(event("run-b-first", run_id="run-b"))
    repository.append(event("run-a-second", run_id="run-a"))
    repository.append(event("run-b-second", run_id="run-b"))

    assert tuple(
        item.id for item in repository.list_by_run("run-a")
    ) == ("run-a-first", "run-a-second")
    assert tuple(
        item.id for item in repository.list_by_run("run-b")
    ) == ("run-b-first", "run-b-second")


def test_contract_backends_have_ordering_parity(tmp_path: Path) -> None:
    repositories: tuple[TimelineRepository, ...] = (
        InMemoryTimelineRepository(),
        FileTimelineRepository(tmp_path / "parity.json"),
        SQLiteTimelineRepository(tmp_path / "parity.db"),
    )

    for current in repositories:
        current.append(event("z"))
        current.append(event("a"))
        current.append(
            event("later", timestamp=NOW + timedelta(seconds=1))
        )

    sequences = tuple(
        tuple(item.id for item in current.list_by_run("run"))
        for current in repositories
    )

    assert sequences == (
        ("z", "a", "later"),
        ("z", "a", "later"),
        ("z", "a", "later"),
    )


def test_contract_allows_equal_content_with_distinct_ids(
    repository: TimelineRepository,
) -> None:
    repository.append(event("a", message="same"))
    repository.append(event("b", message="same"))

    assert len(repository.list_by_run("run")) == 2


def test_contract_rejects_duplicate_id_globally(
    repository: TimelineRepository,
) -> None:
    repository.append(event("same", run_id="run-a"))

    with pytest.raises(DuplicateTimelineEventError, match="same"):
        repository.append(event("same", run_id="run-b"))


def test_contract_rejects_blank_run_query(
    repository: TimelineRepository,
) -> None:
    with pytest.raises(ValueError, match="run_id"):
        repository.list_by_run(" ")
