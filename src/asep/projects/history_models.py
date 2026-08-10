from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from asep.ai_runtime import AIRuntimeExecutionMode, AIRuntimeUsage
from asep.workspace_changes import WorkspaceChange


class ProjectExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProjectSession(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    @field_validator("session_id", "project_id", "title")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("session fields must not be blank")
        return normalized

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session timestamps must be timezone-aware")
        return value


class ProjectExecution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    session_id: str
    project_id: str
    runtime_id: str
    instruction: str
    execution_mode: AIRuntimeExecutionMode
    status: ProjectExecutionStatus
    output: str | None = None
    model: str | None = None
    usage: AIRuntimeUsage | None = None
    changes: tuple[WorkspaceChange, ...] = ()
    error_code: str | None = None
    context_entry_count: int = Field(default=0, ge=0)
    context_truncated: bool = False
    context_char_count: int = Field(default=0, ge=0)
    context_omitted_execution_count: int = Field(default=0, ge=0)
    memory_entry_count: int = Field(default=0, ge=0)
    memory_char_count: int = Field(default=0, ge=0)
    memory_truncated: bool = False
    created_at: datetime
    completed_at: datetime | None = None

    @field_validator("execution_id", "session_id", "project_id", "runtime_id", "instruction")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("execution fields must not be blank")
        return normalized

    @field_validator("created_at", "completed_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("execution timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def terminal_state_is_consistent(self) -> "ProjectExecution":
        terminal = self.status in {
            ProjectExecutionStatus.SUCCEEDED,
            ProjectExecutionStatus.FAILED,
        }
        if terminal != (self.completed_at is not None):
            raise ValueError("terminal execution must have completed_at")
        if self.status is ProjectExecutionStatus.SUCCEEDED and self.error_code is not None:
            raise ValueError("succeeded execution cannot have error_code")
        if self.status is ProjectExecutionStatus.FAILED and not self.error_code:
            raise ValueError("failed execution must have error_code")
        return self


__all__ = ["ProjectExecution", "ProjectExecutionStatus", "ProjectSession"]
