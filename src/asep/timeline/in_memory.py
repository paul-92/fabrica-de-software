"""Implementação não durável do TimelineRepository."""

from __future__ import annotations

from asep.timeline.errors import DuplicateTimelineEventError
from asep.timeline.models import TimelineEvent


class InMemoryTimelineRepository:
    """Mantém cópias de eventos apenas durante a vida desta instância."""

    def __init__(self) -> None:
        self._events: dict[str, TimelineEvent] = {}
        self._event_ids_by_run: dict[str, list[str]] = {}

    def append(self, event: TimelineEvent) -> None:
        if event.id in self._events:
            raise DuplicateTimelineEventError(
                f"Evento de Timeline duplicado: {event.id}"
            )
        stored = self._copy(event)
        self._events[stored.id] = stored
        self._event_ids_by_run.setdefault(stored.run_id, []).append(stored.id)

    def list_by_run(self, run_id: str) -> tuple[TimelineEvent, ...]:
        if not run_id.strip():
            raise ValueError("run_id da consulta não pode ser vazio")
        events = (
            self._events[event_id]
            for event_id in self._event_ids_by_run.get(run_id, ())
        )
        return tuple(
            self._copy(event)
            for event in sorted(
                events,
                key=lambda item: item.timestamp,
            )
        )

    @staticmethod
    def _copy(event: TimelineEvent) -> TimelineEvent:
        return TimelineEvent.model_validate(
            event.model_dump(mode="json")
        )
