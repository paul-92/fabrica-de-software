from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from typer.testing import CliRunner

import asep.cli as cli_module
from asep.application import RunQueryService
from asep.cli import app
from asep.runs import InMemoryRunRepository, Run, RunError, RunStatus
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEvent,
    TimelineEventType,
)

START = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def run(
    run_id: str,
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


def event(
    event_id: str,
    run_id: str,
    *,
    timestamp: datetime = START,
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


@pytest.fixture
def history(monkeypatch: pytest.MonkeyPatch):
    runs = InMemoryRunRepository()
    timeline = InMemoryTimelineRepository()
    service = RunQueryService(runs, timeline)
    monkeypatch.setattr(
        cli_module,
        "run_query_service_provider",
        lambda: service,
    )
    return runs, timeline


@pytest.mark.parametrize(
    "arguments",
    [
        ["--help"],
        ["runs", "--help"],
        ["run", "--help"],
        ["run", "show", "--help"],
        ["run", "timeline", "--help"],
    ],
)
def test_history_command_help(arguments: list[str]) -> None:
    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 0


def test_root_help_lists_history_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert "runs" in result.stdout
    assert "run-show" not in result.stdout
    assert "run-timeline" not in result.stdout

    run_help = CliRunner().invoke(app, ["run", "--help"])
    assert "show" in run_help.stdout
    assert "timeline" in run_help.stdout


@pytest.mark.parametrize("command", ["run-show", "run-timeline"])
def test_flat_history_commands_are_not_registered(command: str) -> None:
    result = CliRunner().invoke(app, [command, "run-id"])

    assert result.exit_code == 2
    assert "No such command" in result.output


@pytest.mark.parametrize("action", ["show", "timeline"])
def test_hierarchical_query_requires_run_id(
    history,
    action: str,
) -> None:
    result = CliRunner().invoke(app, ["run", action])

    assert result.exit_code == 2
    assert "run_id" in result.output
    assert f"run {action}" in result.output
    assert "Traceback" not in result.output


def test_runs_reports_empty_repository(history) -> None:
    result = CliRunner().invoke(app, ["runs"])

    assert result.exit_code == 0
    assert result.stdout == "No runs found.\n"
    assert result.stderr == ""


def test_runs_lists_fields_in_deterministic_order(history) -> None:
    runs, _ = history
    runs.save(run("old", project_id="alpha"))
    runs.save(
        run(
            "new",
            status=RunStatus.RUNNING,
            started_at=START + timedelta(seconds=1),
        )
    )

    result = CliRunner().invoke(app, ["runs"])

    assert result.exit_code == 0
    assert result.stdout.index("new") < result.stdout.index("old")
    assert "STATUS" in result.stdout
    assert "PROJECT" in result.stdout
    assert "running" in result.stdout
    assert "2026-07-29T12:00:01Z" in result.stdout
    assert "running" in result.stdout
    assert "\x1b[" not in result.stdout


def test_runs_filters_by_status(history) -> None:
    runs, _ = history
    runs.save(run("failed", status=RunStatus.FAILED))
    runs.save(run("active", status=RunStatus.RUNNING))

    result = CliRunner().invoke(app, ["runs", "--status", "failed"])

    assert result.exit_code == 0
    assert "failed" in result.stdout
    assert "active" not in result.stdout


def test_runs_rejects_invalid_status_without_traceback(history) -> None:
    result = CliRunner().invoke(
        app, ["runs", "--status", "unknown-status"]
    )

    assert result.exit_code == 2
    assert "unknown-status" in result.output
    assert "Traceback" not in result.output


def test_run_show_formats_optional_duration_metadata_and_error(history) -> None:
    runs, _ = history
    runs.save(
        run(
            "failed-run",
            status=RunStatus.FAILED,
            finished_at=START + timedelta(minutes=2, seconds=3),
            workflow_id="workflow",
            summary="Stopped.",
            error=RunError(
                type="ProviderError",
                message="Unavailable.",
                details={"retryable": False, "code": 7},
            ),
            metadata={"z": 2, "a": {"ok": True}},
        )
    )

    result = CliRunner().invoke(app, ["run", "show", "failed-run"])

    assert result.exit_code == 0
    assert "00:02:03" in result.stdout
    assert "ProviderError" in result.stdout
    assert "Unavailable." in result.stdout
    assert '{"code":7,"retryable":false}' in result.stdout
    assert '{"a":{"ok":true},"z":2}' in result.stdout
    assert "Project" in result.stdout
    assert "  -" in result.stdout


def test_run_show_marks_active_duration_without_clock(history) -> None:
    runs, _ = history
    runs.save(run("active", status=RunStatus.RUNNING))

    result = CliRunner().invoke(app, ["run", "show", "active"])

    assert result.exit_code == 0
    assert "Duration" in result.stdout
    assert "running" in result.stdout
    assert "Finished at" in result.stdout


def test_run_show_missing_is_stderr_domain_error(history) -> None:
    result = CliRunner().invoke(app, ["run", "show", "missing"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "RUN_NOT_FOUND" in result.stderr
    assert "missing" in result.stderr
    assert "Próxima ação:" in result.stderr
    assert "Traceback" not in result.output


def test_timeline_is_chronological_and_formats_optional_fields(history) -> None:
    runs, timeline = history
    runs.save(run("run"))
    timeline.append(
        event(
            "last",
            "run",
            timestamp=START + timedelta(seconds=1),
            event_type=TimelineEventType.STAGE_FINISHED,
            stage_id="analysis",
            message="Finished.",
        )
    )
    timeline.append(event("first", "run"))

    result = CliRunner().invoke(app, ["run", "timeline", "run"])

    assert result.exit_code == 0
    assert result.stdout.index("run.started") < result.stdout.index(
        "stage.finished"
    )
    assert "TIMESTAMP" in result.stdout
    assert "TYPE" in result.stdout
    assert "STAGE" in result.stdout
    assert "MESSAGE" in result.stdout
    assert "analysis" in result.stdout


def test_timeline_for_existing_run_can_be_empty(history) -> None:
    runs, _ = history
    runs.save(run("run"))

    result = CliRunner().invoke(app, ["run", "timeline", "run"])

    assert result.exit_code == 0
    assert result.stdout == "No timeline events found.\n"


def test_timeline_for_missing_run_is_stderr_error(history) -> None:
    result = CliRunner().invoke(app, ["run", "timeline", "missing"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "RUN_NOT_FOUND" in result.stderr
    assert "Traceback" not in result.output


def test_cli_uses_injected_service_without_network_or_files(history) -> None:
    runs, _ = history
    runs.save(run("injected"))

    result = CliRunner().invoke(app, ["runs"])

    assert result.exit_code == 0
    assert "injected" in result.stdout
