from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class SessionMemoryKind(StrEnum):
    DECISION = "decision"
    CONSTRAINT = "constraint"
    FACT = "fact"
    ARTIFACT = "artifact"
    GOAL = "goal"


class SessionMemoryEntry(BaseModel):
    """Fato durável explicitamente pertencente a uma ProjectSession."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: str
    session_id: str
    project_id: str
    kind: SessionMemoryKind
    content: str
    source_execution_id: str | None = None
    created_at: datetime

    @field_validator(
        "memory_id", "session_id", "project_id", "content", "source_execution_id"
    )
    @classmethod
    def text_is_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("session memory text must not be blank")
        return value.strip() if value is not None else None

    @field_validator("created_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session memory timestamp must be timezone-aware")
        return value

    @property
    def is_manual(self) -> bool:
        return self.source_execution_id is None


__all__ = ["SessionMemoryEntry", "SessionMemoryKind"]
