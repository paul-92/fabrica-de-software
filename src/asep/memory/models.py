"""Modelos imutáveis da memória operacional de agentes."""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum, StrEnum
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
from asep.agents.contracts import AgentId


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MemoryId(_FrozenModel):
    value: str

    @field_validator("value")
    @classmethod
    def value_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("MemoryId não pode ser vazio")
        return value

    def __str__(self) -> str:
        return self.value


class MemoryCategory(StrEnum):
    FACT = "fact"
    DECISION = "decision"
    OBSERVATION = "observation"
    PLAN = "plan"
    TASK = "task"
    ERROR = "error"
    RESULT = "result"
    SYSTEM = "system"
    CUSTOM = "custom"


class MemoryImportance(IntEnum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MemoryEntry(_FrozenModel):
    memory_id: MemoryId
    agent_id: AgentId
    execution_id: str
    workflow_execution_id: str | None = None
    category: MemoryCategory
    importance: MemoryImportance = MemoryImportance.NORMAL
    content: str = Field(repr=False)
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict, repr=False)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None

    @field_validator("execution_id", "workflow_execution_id", "content")
    @classmethod
    def text_is_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("texto de memória não pode ser vazio")
        return value

    @field_validator("created_at", "updated_at", "expires_at")
    @classmethod
    def timestamp_is_aware(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("timestamp deve possuir timezone")
        return value

    @model_validator(mode="after")
    def timestamps_are_consistent(self) -> MemoryEntry:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at não pode preceder created_at")
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at deve suceder created_at")
        return self


class MemoryQuery(_FrozenModel):
    agent_id: AgentId | None = None
    category: MemoryCategory | None = None
    text: str | None = None
    execution_id: str | None = None
    workflow_execution_id: str | None = None
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator("text", "execution_id", "workflow_execution_id")
    @classmethod
    def optional_text_is_not_blank(
        cls, value: str | None
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("filtro textual não pode ser vazio")
        return value


class MemoryRetentionPolicy(_FrozenModel):
    max_entries: int = Field(default=1000, ge=1)
    expiration_seconds: float | None = Field(default=None, gt=0)
    max_context_size: int = Field(default=32_000, ge=1)
    remove_expired: bool = True
    remove_low_priority: bool = True
    compress_old_entries: bool = False


class ContextBuildRequest(_FrozenModel):
    agent_id: AgentId
    execution_id: str
    workflow_execution_id: str | None = None
    workflow_context: Mapping[str, JsonValue] = Field(
        default_factory=dict, repr=False
    )
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict, repr=False)

    @field_validator("execution_id", "workflow_execution_id")
    @classmethod
    def identity_is_not_blank(
        cls, value: str | None
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identificador não pode ser vazio")
        return value


class ContextBuildResult(_FrozenModel):
    context: Mapping[str, Any] = Field(default_factory=dict, repr=False)
    memories: tuple[MemoryEntry, ...] = ()
    truncated: bool = False
    duration_seconds: float = Field(default=0, ge=0)

    @field_validator("context")
    @classmethod
    def context_is_json(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return freeze_json(value, location="memory context")

    @field_serializer("context")
    def serialize_context(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return json_value(value)


__all__ = [
    "ContextBuildRequest",
    "ContextBuildResult",
    "MemoryCategory",
    "MemoryEntry",
    "MemoryId",
    "MemoryImportance",
    "MemoryQuery",
    "MemoryRetentionPolicy",
]
