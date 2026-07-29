"""Serviço de aplicação para criação e registro de eventos."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from asep.timeline.models import TimelineEvent, TimelineEventType
from asep.timeline.repository import TimelineRepository

Clock = Callable[[], datetime]
EventIdGenerator = Callable[[], str]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _uuid4_string() -> str:
    return str(uuid4())


class TimelineRecorder:
    def __init__(
        self,
        repository: TimelineRepository,
        *,
        clock: Clock | None = None,
        id_generator: EventIdGenerator | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or _utc_now
        self._id_generator = id_generator or _uuid4_string

    def record(
        self,
        run_id: str,
        event_type: TimelineEventType,
        *,
        stage_id: str | None = None,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TimelineEvent:
        event = TimelineEvent(
            id=self._id_generator(),
            run_id=run_id,
            timestamp=self._clock(),
            type=event_type,
            stage_id=stage_id,
            message=message,
            metadata=metadata or {},
        )
        self._repository.append(event)
        return event

    def record_error(
        self,
        run_id: str,
        error: BaseException,
        *,
        stage_id: str | None = None,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TimelineEvent:
        details = dict(metadata or {})
        details["exception_type"] = type(error).__name__
        neutral_message = message or str(error) or type(error).__name__
        return self.record(
            run_id,
            TimelineEventType.ERROR,
            stage_id=stage_id,
            message=neutral_message,
            metadata=details,
        )
