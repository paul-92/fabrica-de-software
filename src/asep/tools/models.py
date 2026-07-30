"""Modelos públicos, imutáveis e independentes de implementação para Tools."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_serializer,
    field_validator,
    model_validator,
)

from asep._json_values import freeze_json, json_value


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolId(_FrozenModel):
    value: str

    @field_validator("value")
    @classmethod
    def value_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ToolId não pode ser vazio")
        return value

    def __str__(self) -> str:
        return self.value

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ToolId):
            return NotImplemented
        return self.value < other.value


class ToolCapability(_FrozenModel):
    id: str
    description: str | None = None

    @field_validator("id")
    @classmethod
    def id_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("capability não pode ser vazia")
        return value


class ToolMetadata(_FrozenModel):
    id: ToolId
    name: str
    description: str
    version: str
    author: str
    category: str
    capabilities: tuple[ToolCapability, ...]

    @field_validator("name", "description", "version", "author", "category")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("metadata textual não pode ser vazia")
        return value

    @model_validator(mode="after")
    def capabilities_are_unique(self) -> ToolMetadata:
        ids = tuple(item.id for item in self.capabilities)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("capabilities devem existir e ser únicas")
        return self


class ToolExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"


class ToolError(_FrozenModel):
    code: str
    message: str
    retryable: bool = False
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator("code", "message")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code e message são obrigatórios")
        return value


class ToolRequest(_FrozenModel):
    execution_id: str
    tool_id: ToolId
    capability: ToolCapability
    workspace: Path
    payload: Mapping[str, JsonValue] = Field(default_factory=dict, repr=False)
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict, repr=False)
    workflow_execution_id: str | None = None
    correlation_id: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)

    @field_validator(
        "execution_id",
        "workflow_execution_id",
        "correlation_id",
    )
    @classmethod
    def ids_are_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identificador não pode ser vazio")
        return value


class ToolContext(_FrozenModel):
    execution_id: str
    started_at: datetime
    workspace: Path
    attempt: int = Field(default=1, ge=1)
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict, repr=False)
    correlation_id: str | None = None

    @field_validator("started_at")
    @classmethod
    def started_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("started_at deve possuir timezone")
        return value


class ToolResult(_FrozenModel):
    execution_id: str
    tool_id: ToolId
    status: ToolExecutionStatus
    output: Mapping[str, Any] = Field(default_factory=dict, repr=False)
    duration_seconds: float = Field(ge=0)
    started_at: datetime
    completed_at: datetime
    attempts: int = Field(ge=0)
    error: ToolError | None = None
    metadata: Mapping[str, Any] = Field(default_factory=dict, repr=False)

    @field_validator("started_at", "completed_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp deve possuir timezone")
        return value

    @field_validator("output", "metadata")
    @classmethod
    def mappings_are_json(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return freeze_json(value, location="tool result")

    @field_serializer("output", "metadata")
    def serialize_mapping(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return json_value(value)

    @model_validator(mode="after")
    def result_is_consistent(self) -> ToolResult:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at não pode preceder started_at")
        succeeded = self.status is ToolExecutionStatus.SUCCEEDED
        if succeeded == (self.error is not None):
            raise ValueError("status e error são inconsistentes")
        return self


class ToolExecutionPolicy(_FrozenModel):
    timeout_seconds: float | None = Field(default=None, gt=0)
    retry_enabled: bool = False
    max_attempts: int = Field(default=1, ge=1)
    fail_fast: bool = True

    @model_validator(mode="after")
    def retry_is_consistent(self) -> ToolExecutionPolicy:
        if not self.retry_enabled and self.max_attempts != 1:
            raise ValueError(
                "max_attempts deve ser 1 quando retry está desabilitado"
            )
        return self


__all__ = [
    "ToolCapability",
    "ToolContext",
    "ToolError",
    "ToolExecutionPolicy",
    "ToolExecutionStatus",
    "ToolId",
    "ToolMetadata",
    "ToolRequest",
    "ToolResult",
]

