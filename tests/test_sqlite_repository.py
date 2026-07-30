from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asep.api import create_app, create_default_app
from asep.application import RunQueryService
from asep.configuration import ApplicationSettings
from asep.metrics import MetricsService
from asep.repositories import RepositoryFactory
from asep.runs import (
    InvalidRunStorageFormatError,
    Run,
    RunStatus,
    SQLiteRunRepository,
)
from asep.sqlite import SQLiteConnectionError, SQLiteSchemaError
from asep.timeline import (
    SQLiteTimelineRepository,
    TimelineEvent,
    TimelineEventType,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def make_run(
    *,
    status: RunStatus = RunStatus.RUNNING,
    finished_at: datetime | None = None,
) -> Run:
    return Run(
        id="run",
        status=status,
        started_at=NOW,
        finished_at=finished_at,
        project_id="project",
        workflow_id="workflow",
        stage_id="stage",
        provider_name="codex",
        summary="summary",
        metadata={"nested": {"enabled": True}},
    )


def make_event() -> TimelineEvent:
    return TimelineEvent(
        id="event",
        run_id="run",
        timestamp=NOW,
        type=TimelineEventType.RUN_STARTED,
        stage_id="stage",
        message="started",
        metadata={"attempt": 1},
    )


def test_sqlite_run_persists_update_between_instances(
    tmp_path: Path,
) -> None:
    database = tmp_path / "nested/asep.db"
    first = SQLiteRunRepository(database)
    first.save(make_run())
    updated = make_run(
        status=RunStatus.SUCCEEDED,
        finished_at=NOW + timedelta(seconds=2),
    )
    first.save(updated)

    second = SQLiteRunRepository(database)

    assert second.get("run") == updated
    assert second.list() == (updated,)


def test_sqlite_timeline_persists_between_instances(
    tmp_path: Path,
) -> None:
    database = tmp_path / "asep.db"
    SQLiteTimelineRepository(database).append(make_event())

    restored = SQLiteTimelineRepository(database).list_by_run("run")

    assert restored == (make_event(),)


def test_sqlite_initializes_shared_schema(tmp_path: Path) -> None:
    database = tmp_path / "asep.db"
    SQLiteRunRepository(database)

    with closing(sqlite3.connect(database)) as connection, connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

    assert {"runs", "timeline_events"} <= tables


def test_sqlite_rejects_incompatible_schema(tmp_path: Path) -> None:
    database = tmp_path / "invalid.db"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TABLE runs (wrong TEXT)")

    with pytest.raises(SQLiteSchemaError, match="runs"):
        SQLiteRunRepository(database)


def test_sqlite_reports_connection_failure_for_directory(
    tmp_path: Path,
) -> None:
    with pytest.raises(SQLiteConnectionError, match="abrir"):
        SQLiteRunRepository(tmp_path)


def test_sqlite_reports_invalid_stored_run(tmp_path: Path) -> None:
    database = tmp_path / "asep.db"
    repository = SQLiteRunRepository(database)
    repository.save(make_run())
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "UPDATE runs SET payload = ? WHERE id = ?",
            ("not-json", "run"),
        )

    with pytest.raises(InvalidRunStorageFormatError):
        repository.get("run")


def test_query_metrics_and_dashboard_work_with_sqlite(
    tmp_path: Path,
) -> None:
    settings = ApplicationSettings(
        storage_backend="sqlite",
        sqlite_database=tmp_path / "asep.db",
    )
    repositories = RepositoryFactory(settings).create()
    repositories.run_repository.save(
        make_run(
            status=RunStatus.SUCCEEDED,
            finished_at=NOW + timedelta(seconds=2),
        )
    )
    repositories.timeline_repository.append(make_event())
    query = RunQueryService(
        repositories.run_repository,
        repositories.timeline_repository,
    )
    metrics = MetricsService(query)
    client = TestClient(create_app(query, metrics))

    assert query.get_run("run").provider_name == "codex"
    assert query.get_timeline("run") == (make_event(),)
    assert metrics.get_summary().success_rate == 1
    assert client.get("/api/v1/runs/run").status_code == 200


def test_default_dashboard_composition_accepts_sqlite(
    tmp_path: Path,
) -> None:
    settings = ApplicationSettings(
        storage_backend="sqlite",
        sqlite_database=tmp_path / "dashboard.db",
    )

    response = TestClient(create_default_app(settings)).get(
        "/api/v1/runs"
    )

    assert response.json() == {"items": []}
    assert (tmp_path / "dashboard.db").exists()
