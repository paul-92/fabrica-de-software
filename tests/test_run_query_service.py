from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from asep.application import RunQueryService
from asep.errors import RunNotFoundError
from asep.runs import (
    InMemoryRunRepository,
    Run,
    RunRepository,
    RunStatus,
)
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEvent,
    TimelineEventType,
    TimelineRepository,
)

START = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def make_run(
    run_id: str,
    *,
    started_at: datetime = START,
    status: RunStatus = RunStatus.PENDING,
    **values,
) -> Run:
    return Run(
        id=run_id,
        started_at=started_at,
        status=status,
        **values,
    )


def make_event(
    event_id: str,
    run_id: str,
    *,
    timestamp: datetime = START,
) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        run_id=run_id,
        timestamp=timestamp,
        type=TimelineEventType.RUN_STARTED,
    )


def service_with(
    *runs: Run,
    events: tuple[TimelineEvent, ...] = (),
) -> RunQueryService:
    run_repository = InMemoryRunRepository()
    timeline_repository = InMemoryTimelineRepository()
    for run in runs:
        run_repository.save(run)
    for event in events:
        timeline_repository.append(event)
    return RunQueryService(run_repository, timeline_repository)


def test_constructs_with_repository_contracts() -> None:
    runs: RunRepository = InMemoryRunRepository()
    timeline: TimelineRepository = InMemoryTimelineRepository()

    service = RunQueryService(runs, timeline)

    assert service.list_runs() == ()


def test_lists_empty_repository() -> None:
    assert service_with().list_runs() == ()


def test_lists_one_run() -> None:
    run = make_run("one")

    assert service_with(run).list_runs() == (run,)


def test_lists_runs_most_recent_first() -> None:
    old = make_run("old", started_at=START)
    new = make_run("new", started_at=START + timedelta(minutes=1))

    assert service_with(new, old).list_runs() == (new, old)


def test_list_uses_ascending_id_as_stable_tie_breaker() -> None:
    first = make_run("a")
    last = make_run("z")

    assert service_with(first, last).list_runs() == (first, last)


def test_gets_existing_run_as_repository_snapshot() -> None:
    source = make_run("known", metadata={"nested": {"value": 1}})
    service = service_with(source)

    selected = service.get_run("known")

    assert selected == source
    assert selected is not source
    assert selected.metadata is not source.metadata


def test_get_missing_run_uses_existing_domain_error() -> None:
    with pytest.raises(RunNotFoundError, match="missing"):
        service_with().get_run("missing")


@pytest.mark.parametrize("run_id", ["", " ", "\t"])
def test_get_rejects_empty_run_id(run_id: str) -> None:
    with pytest.raises(ValueError, match="run_id"):
        service_with().get_run(run_id)


def test_returns_latest_run() -> None:
    old = make_run("old")
    new = make_run("new", started_at=START + timedelta(seconds=1))

    assert service_with(new, old).latest_run() == new


def test_latest_run_uses_same_tie_breaker_as_list() -> None:
    assert service_with(make_run("a"), make_run("z")).latest_run().id == "a"


def test_latest_without_runs_is_explicit() -> None:
    with pytest.raises(RunNotFoundError, match="Nenhum Run"):
        service_with().latest_run()


def test_filters_by_typed_status_and_preserves_order() -> None:
    failed_old = make_run("old", status=RunStatus.FAILED)
    running = make_run(
        "running",
        status=RunStatus.RUNNING,
        started_at=START + timedelta(minutes=1),
    )
    failed_new = make_run(
        "new",
        status=RunStatus.FAILED,
        started_at=START + timedelta(minutes=2),
    )

    assert service_with(
        failed_old, running, failed_new
    ).list_runs_by_status(RunStatus.FAILED) == (failed_new, failed_old)


def test_filter_without_matches_is_empty() -> None:
    assert service_with(
        make_run("one")
    ).list_runs_by_status(RunStatus.CANCELLED) == ()


def test_filter_rejects_arbitrary_string() -> None:
    with pytest.raises(TypeError, match="RunStatus"):
        service_with().list_runs_by_status("failed")  # type: ignore[arg-type]


def test_timeline_for_existing_run_is_chronological() -> None:
    run = make_run("run")
    first = make_event("first", "run")
    last = make_event(
        "last", "run", timestamp=START + timedelta(seconds=1)
    )

    assert service_with(
        run, events=(last, first)
    ).get_timeline("run") == (first, last)


def test_timeline_uses_id_as_ascending_tie_breaker() -> None:
    run = make_run("run")
    a = make_event("a", "run")
    z = make_event("z", "run")

    assert service_with(run, events=(z, a)).get_timeline("run") == (a, z)


def test_timeline_for_existing_run_without_events_is_empty() -> None:
    assert service_with(make_run("run")).get_timeline("run") == ()


def test_timeline_for_missing_run_is_explicit() -> None:
    with pytest.raises(RunNotFoundError, match="missing"):
        service_with().get_timeline("missing")


def test_timeline_does_not_expose_repository_objects() -> None:
    event = make_event("event", "run")
    service = service_with(make_run("run"), events=(event,))

    first = service.get_timeline("run")
    second = service.get_timeline("run")

    assert first is not second
    assert first[0] is not second[0]


def test_supports_active_finished_optional_and_structured_runs() -> None:
    active = make_run("active", status=RunStatus.RUNNING)
    finished = make_run(
        "finished",
        status=RunStatus.SUCCEEDED,
        finished_at=START + timedelta(seconds=4),
        project_id="project",
        metadata={"attempt": 1},
    )

    assert service_with(active, finished).get_run("active").finished_at is None
    assert service_with(active, finished).get_run("finished") == finished


def test_service_depends_on_protocol_behavior_not_concrete_classes() -> None:
    run = make_run("run")

    class RunsStub:
        def save(self, run: Run) -> None:
            raise AssertionError("query service must not save")

        def get(self, run_id: str) -> Run:
            assert run_id == "run"
            return run

        def list(self) -> tuple[Run, ...]:
            return (run,)

    class TimelineStub:
        def append(self, event: TimelineEvent) -> None:
            raise AssertionError("query service must not append")

        def list_by_run(self, run_id: str) -> tuple[TimelineEvent, ...]:
            assert run_id == "run"
            return ()

    service = RunQueryService(RunsStub(), TimelineStub())

    assert service.get_run("run") == run
    assert service.get_timeline("run") == ()
