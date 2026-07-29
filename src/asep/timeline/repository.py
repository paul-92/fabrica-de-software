"""Porta de persistência neutra para eventos de Timeline."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from asep.timeline.models import TimelineEvent


@runtime_checkable
class TimelineRepository(Protocol):
    def append(self, event: TimelineEvent) -> None: ...

    def list_by_run(self, run_id: str) -> tuple[TimelineEvent, ...]: ...
