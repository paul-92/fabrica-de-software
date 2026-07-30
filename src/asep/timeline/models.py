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
    AGENT_EXECUTION_REQUESTED = "agent_execution_requested"
    AGENT_EXECUTION_VALIDATED = "agent_execution_validated"
    AGENT_EXECUTION_STARTED = "agent_execution_started"
    AGENT_EXECUTION_SUCCEEDED = "agent_execution_succeeded"
    AGENT_EXECUTION_FAILED = "agent_execution_failed"
    AGENT_EXECUTION_REJECTED = "agent_execution_rejected"
    AGENT_EXECUTION_RETRYING = "agent_execution_retrying"
    AGENT_EXECUTION_TIMED_OUT = "agent_execution_timed_out"
    AGENT_EXECUTION_CANCELLED = "agent_execution_cancelled"
    TOOL_REQUESTED = "tool_requested"
    TOOL_VALIDATED = "tool_validated"
    TOOL_STARTED = "tool_started"
    TOOL_SUCCEEDED = "tool_succeeded"
    TOOL_FAILED = "tool_failed"
    TOOL_REJECTED = "tool_rejected"
    TOOL_TIMEOUT = "tool_timeout"
    MEMORY_SAVED = "memory_saved"
    MEMORY_LOADED = "memory_loaded"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_DELETED = "memory_deleted"
    MEMORY_EXPIRED = "memory_expired"
    MEMORY_FILTERED = "memory_filtered"
    CONTEXT_BUILT = "context_built"
    PLANNING_REQUESTED = "planning_requested"
    PLANNING_STARTED = "planning_started"
    PLANNING_COMPLETED = "planning_completed"
    PLANNING_FAILED = "planning_failed"
    PLAN_VALIDATED = "plan_validated"
    PLAN_REJECTED = "plan_rejected"
    COORDINATION_STARTED = "coordination_started"
    AGENT_SELECTED = "agent_selected"
    ASSIGNMENT_CREATED = "assignment_created"
    ASSIGNMENT_COMPLETED = "assignment_completed"
    COORDINATION_COMPLETED = "coordination_completed"
    COORDINATION_FAILED = "coordination_failed"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    RETRY_STARTED = "retry_started"
    RETRY_COMPLETED = "retry_completed"
    RETRY_FAILED = "retry_failed"
    FALLBACK_STARTED = "fallback_started"
    FALLBACK_COMPLETED = "fallback_completed"
    FALLBACK_FAILED = "fallback_failed"
    RECOVERY_COMPLETED = "recovery_completed"
    EXECUTION_CANCELLED = "execution_cancelled"


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
