"""Modelos imutáveis da coordenação multiagente."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from asep.agents.contracts import AgentId
from asep.agents.runtime_models import AgentExecutionResult
from asep.memory.models import MemoryEntry
from asep.planning.models import ExecutionPlan


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AssignmentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CoordinationStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class AgentAssignment(_FrozenModel):
    assignment_id: str
    plan_step_id: str
    agent_id: AgentId
    required_capability: str
    priority: int = Field(ge=0)
    status: AssignmentStatus = AssignmentStatus.PENDING
    created_at: datetime
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator(
        "assignment_id", "plan_step_id", "required_capability"
    )
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identificador de assignment não pode ser vazio")
        return value

    @field_validator("created_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at deve possuir timezone")
        return value


class AgentSelectionPolicy(_FrozenModel):
    prefer_explicit_agent: bool = True
    require_available: bool = True
    affinity: Mapping[str, str] = Field(default_factory=dict)
    unavailable_agents: tuple[str, ...] = ()


class CoordinationPolicy(_FrozenModel):
    max_agents: int = Field(default=100, ge=1)
    max_assignments: int = Field(default=100, ge=1)
    order: str = "dependencies_then_priority"
    logical_timeout_seconds: float | None = Field(default=None, gt=0)
    stop_on_failure: bool = True
    allow_fallback: bool = True
    selection: AgentSelectionPolicy = Field(
        default_factory=AgentSelectionPolicy
    )

    @field_validator("order")
    @classmethod
    def supported_order(cls, value: str) -> str:
        if value not in {"dependencies_then_priority", "plan"}:
            raise ValueError("ordem de coordenação não suportada")
        return value


class CoordinationContext(_FrozenModel):
    execution_plan: ExecutionPlan
    workflow: Mapping[str, JsonValue] = Field(default_factory=dict)
    memory: tuple[MemoryEntry, ...] = ()
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)
    assignments: tuple[AgentAssignment, ...] = ()
    partial_results: tuple[AgentExecutionResult, ...] = ()


class CoordinationStatistics(_FrozenModel):
    assignments_total: int = Field(ge=0)
    completed_total: int = Field(ge=0)
    failed_total: int = Field(ge=0)
    agents_used: int = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    aggregation_duration_seconds: float = Field(ge=0)


class CoordinationResult(_FrozenModel):
    plan_id: str
    run_id: str
    status: CoordinationStatus
    assignments: tuple[AgentAssignment, ...]
    results: tuple[AgentExecutionResult, ...]
    output: Mapping[str, JsonValue] = Field(default_factory=dict)
    statistics: CoordinationStatistics


__all__ = [
    "AgentAssignment",
    "AgentSelectionPolicy",
    "AssignmentStatus",
    "CoordinationContext",
    "CoordinationPolicy",
    "CoordinationResult",
    "CoordinationStatistics",
    "CoordinationStatus",
]
