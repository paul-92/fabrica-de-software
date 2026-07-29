"""Formatação textual determinística do histórico de Runs."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from asep._json_values import json_value
from asep.runs import Run
from asep.timeline import TimelineEvent

EMPTY_VALUE = "-"


def format_runs(runs: Sequence[Run]) -> str:
    if not runs:
        return "No runs found."
    rows = [
        (
            run.id,
            run.status.value,
            _optional(run.project_id),
            _optional(run.stage_id),
            _timestamp(run.started_at),
            _timestamp(run.finished_at),
            _duration(run),
        )
        for run in runs
    ]
    return _table(
        ("ID", "STATUS", "PROJECT", "STAGE", "STARTED", "FINISHED", "DURATION"),
        rows,
    )


def format_run(run: Run) -> str:
    values = [
        ("Run ID", run.id),
        ("Status", run.status.value),
        ("Project", _optional(run.project_id)),
        ("Workflow", _optional(run.workflow_id)),
        ("Stage", _optional(run.stage_id)),
        ("Provider", _optional(run.provider_name)),
        ("Started at", _timestamp(run.started_at)),
        ("Finished at", _timestamp(run.finished_at)),
        ("Duration", _duration(run)),
        ("Summary", _optional(run.summary)),
    ]
    if run.error is None:
        values.extend(
            (
                ("Error type", EMPTY_VALUE),
                ("Error message", EMPTY_VALUE),
                ("Error details", EMPTY_VALUE),
            )
        )
    else:
        values.extend(
            (
                ("Error type", run.error.type),
                ("Error message", run.error.message),
                ("Error details", _json(run.error.details)),
            )
        )
    values.append(("Metadata", _json(run.metadata)))
    width = max(len(label) for label, _ in values)
    return "\n".join(
        f"{label:<{width}}  {value}" for label, value in values
    )


def format_timeline(events: Sequence[TimelineEvent]) -> str:
    if not events:
        return "No timeline events found."
    rows = [
        (
            _timestamp(event.timestamp),
            event.type.value,
            _optional(event.stage_id),
            _optional(event.message),
        )
        for event in events
    ]
    return _table(("TIMESTAMP", "TYPE", "STAGE", "MESSAGE"), rows)


def _table(
    headers: tuple[str, ...],
    rows: Sequence[tuple[str, ...]],
) -> str:
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    lines = [
        "  ".join(
            header.ljust(widths[index])
            for index, header in enumerate(headers)
        )
    ]
    lines.extend(
        "  ".join(
            value.ljust(widths[index])
            for index, value in enumerate(row)
        ).rstrip()
        for row in rows
    )
    return "\n".join(lines)


def _optional(value: str | None) -> str:
    return value if value is not None else EMPTY_VALUE


def _timestamp(value: datetime | None) -> str:
    if value is None:
        return EMPTY_VALUE
    return value.isoformat().replace("+00:00", "Z")


def _duration(run: Run) -> str:
    if run.finished_at is None:
        return "running"
    return _format_timedelta(run.finished_at - run.started_at)


def _format_timedelta(value: timedelta) -> str:
    total_seconds = int(value.total_seconds())
    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)
    clock = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{days}d {clock}" if days else clock


def _json(value: Mapping[str, Any]) -> str:
    if not value:
        return "{}"
    return json.dumps(
        json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
