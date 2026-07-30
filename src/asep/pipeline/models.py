"""Modelos públicos do pipeline ponta a ponta."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from asep.agents.coordination.models import AgentAssignment
from asep.memory.models import MemoryEntry
from asep.planning.models import ExecutionPlan
from asep.timeline.models import TimelineEvent


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoalStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalRequest(_FrozenModel):
    goal: str
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)
    workspace: Path
    options: Mapping[str, JsonValue] = Field(default_factory=dict)
    created_at: datetime

    @field_validator("goal")
    @classmethod
    def goal_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("goal não pode ser vazio")
        return value

    @field_validator("created_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at deve possuir timezone")
        return value


class GoalExecutionContext(_FrozenModel):
    run_id: str
    workflow: Mapping[str, JsonValue]
    execution_plan: ExecutionPlan | None = None
    memory: tuple[MemoryEntry, ...] = ()
    assignments: tuple[AgentAssignment, ...] = ()
    timeline: tuple[TimelineEvent, ...] = ()
    metrics: Mapping[str, JsonValue] = Field(default_factory=dict)
    workspace: Path


class GoalResult(_FrozenModel):
    run_id: str
    status: GoalStatus
    summary: str
    steps: tuple[Mapping[str, JsonValue], ...] = ()
    timeline: tuple[TimelineEvent, ...] = ()
    metrics: Mapping[str, JsonValue] = Field(default_factory=dict)
    execution_time: float = Field(ge=0)
    artifacts: tuple[Mapping[str, JsonValue], ...] = ()
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)


__all__ = [
    "GoalExecutionContext",
    "GoalRequest",
    "GoalResult",
    "GoalStatus",
]
