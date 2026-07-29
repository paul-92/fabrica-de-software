"""Modelos neutros e serializáveis de uma execução rastreável."""

from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


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


def _freeze_json(value: Any, *, location: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{location} contém número não finito")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError(f"{location} deve usar apenas chaves string")
        return MappingProxyType(
            {
                key: _freeze_json(item, location=f"{location}.{key}")
                for key, item in value.items()
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        )
    raise ValueError(
        f"{location} contém tipo não serializável: {type(value).__name__}"
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _json_value(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


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
        return _freeze_json(value, location="error.details")

    @field_serializer("details")
    def serialize_details(
        self, value: Mapping[str, Any]
    ) -> dict[str, Any]:
        return _json_value(value)


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
        return _freeze_json(value, location="metadata")

    @field_serializer("metadata")
    def serialize_metadata(
        self, value: Mapping[str, Any]
    ) -> dict[str, Any]:
        return _json_value(value)

    @model_validator(mode="after")
    def timestamps_are_consistent(self) -> Run:
        if (
            self.finished_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("finished_at não pode preceder started_at")
        return self
