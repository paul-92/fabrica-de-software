"""Modelos neutros e serializáveis de uma execução rastreável."""

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
    model_validator,
)

from asep._json_values import freeze_json, json_value


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }


class RunError(BaseModel):
    """Representação neutra de uma falha, sem exceções Python."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str
    message: str
    details: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("type", "message")
    @classmethod
    def text_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tipo e mensagem do erro não podem ser vazios")
        return value

    @field_validator("details")
    @classmethod
    def details_are_json(
        cls, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        return freeze_json(value, location="error.details")

    @field_serializer("details")
    def serialize_details(
        self, value: Mapping[str, Any]
    ) -> dict[str, Any]:
        return json_value(value)


class Run(BaseModel):
    """Snapshot imutável de uma execução conhecido pelo repositório."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    status: RunStatus = RunStatus.PENDING
    started_at: datetime
    finished_at: datetime | None = None
    project_id: str | None = None
    workflow_id: str | None = None
    stage_id: str | None = None
    provider_name: str | None = None
    summary: str | None = None
    error: RunError | None = None
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def identity_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id do Run não pode ser vazio")
        return value

    @field_validator(
        "project_id",
        "workflow_id",
        "stage_id",
        "provider_name",
        "summary",
    )
    @classmethod
    def optional_text_is_not_blank(
        cls, value: str | None
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("campo textual opcional não pode ser vazio")
        return value

    @field_validator("started_at", "finished_at")
    @classmethod
    def timestamp_is_timezone_aware(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
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

    @model_validator(mode="after")
    def timestamps_are_consistent(self) -> Run:
        if (
            self.finished_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("finished_at não pode preceder started_at")
        return self
