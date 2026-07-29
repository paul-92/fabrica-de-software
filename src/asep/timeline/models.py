"""Modelos neutros e imutáveis da Timeline de execução."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)

from asep._json_values import freeze_json, json_value


class TimelineEventType(StrEnum):
    RUN_STARTED = "run.started"
    RUN_FINISHED = "run.finished"
    STAGE_STARTED = "stage.started"
    STAGE_FINISHED = "stage.finished"
    PROVIDER_STARTED = "provider.started"
    PROVIDER_FINISHED = "provider.finished"
    WARNING = "warning"
    ERROR = "error"


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    run_id: str
    timestamp: datetime
    type: TimelineEventType
    stage_id: str | None = None
    message: str | None = None
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("id", "run_id")
    @classmethod
    def identity_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id e run_id não podem ser vazios")
        return value

    @field_validator("stage_id", "message")
    @classmethod
    def optional_text_is_not_blank(
        cls, value: str | None
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("campo textual opcional não pode ser vazio")
        return value

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp deve possuir timezone")
        return value

    @field_validator("metadata")
    @classmethod
    def metadata_is_json(
        cls, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        return freeze_json(value, location="metadata")

    @field_serializer("metadata")
    def serialize_metadata(
        self, value: Mapping[str, Any]
    ) -> dict[str, Any]:
        return json_value(value)
