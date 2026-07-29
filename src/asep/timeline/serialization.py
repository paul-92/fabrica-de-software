"""Serialização explícita de TimelineEvent para armazenamento JSON."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import ValidationError

from asep.timeline.errors import InvalidTimelineStorageFormatError
from asep.timeline.models import TimelineEvent


class TimelineEventCodec:
    @staticmethod
    def encode(event: TimelineEvent) -> dict[str, Any]:
        serialized = event.model_dump(mode="json")
        return {
            "id": serialized["id"],
            "run_id": serialized["run_id"],
            "timestamp": serialized["timestamp"],
            "type": serialized["type"],
            "stage_id": serialized["stage_id"],
            "message": serialized["message"],
            "metadata": serialized["metadata"],
        }

    @staticmethod
    def decode(data: Mapping[str, Any]) -> TimelineEvent:
        try:
            return TimelineEvent.model_validate(data)
        except (TypeError, ValidationError) as exc:
            raise InvalidTimelineStorageFormatError(
                "Evento persistido possui formato inválido."
            ) from exc
