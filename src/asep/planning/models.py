"""Modelos imutáveis do planejamento determinístico."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
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
from asep.memory.models import MemoryEntry
from asep.tools.models import ToolId


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlanStepStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(_FrozenModel):
    step_id: str
    description: str
    required_capability: str
    tool_id: ToolId | None = None
    agent_id: AgentId | None = None
    dependencies: tuple[str, ...] = ()
    priority: int = Field(default=0, ge=0)
    status: PlanStepStatus = PlanStepStatus.PENDING
    estimated_cost: float = Field(default=0, ge=0)
    estimated_duration_seconds: float = Field(default=0, ge=0)
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator("step_id", "description", "required_capability")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório do PlanStep não pode ser vazio")
        return value

    @model_validator(mode="after")
    def dependencies_are_valid(self) -> PlanStep:
        if self.step_id in self.dependencies:
            raise ValueError("PlanStep não pode depender de si próprio")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("PlanStep possui dependências duplicadas")
        return self


class ExecutionPlan(_FrozenModel):
    plan_id: str
    goal: str
    steps: tuple[PlanStep, ...]
    estimated_cost: float = Field(ge=0)
    estimated_duration_seconds: float = Field(ge=0)
    created_at: datetime
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator("plan_id", "goal")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("plan_id e goal não podem ser vazios")
        return value

    @field_validator("created_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at deve possuir timezone")
        return value


class PlanningContext(_FrozenModel):
    objective: str
    memory: tuple[MemoryEntry, ...] = ()
    workflow: Mapping[str, JsonValue] = Field(default_factory=dict, repr=False)
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict, repr=False)
    constraints: tuple[str, ...] = ()
    available_capabilities: tuple[str, ...] = ()
    available_tools: Mapping[str, str] = Field(default_factory=dict)

    @field_validator("objective")
    @classmethod
    def objective_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("objective não pode ser vazio")
        return value

    @model_validator(mode="after")
    def capabilities_are_unique(self) -> PlanningContext:
        if len(self.available_capabilities) != len(
            set(self.available_capabilities)
        ):
            raise ValueError("available_capabilities possui duplicatas")
        return self


class PlanningRequest(_FrozenModel):
    goal: str
    context: PlanningContext
    workflow_execution_id: str | None = None
    agent_id: AgentId | None = None
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict, repr=False)

    @field_validator("goal", "workflow_execution_id")
    @classmethod
    def text_is_not_blank(
        cls, value: str | None
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("texto de PlanningRequest não pode ser vazio")
        return value


class PlanningPolicy(_FrozenModel):
    max_steps: int = Field(default=100, ge=1)
    max_depth: int = Field(default=100, ge=1)
    rules: Mapping[str, JsonValue] = Field(default_factory=dict)
    priorities: Mapping[str, int] = Field(default_factory=dict)
    max_estimated_cost: float | None = Field(default=None, ge=0)

    @field_validator("priorities")
    @classmethod
    def priorities_are_non_negative(
        cls, value: Mapping[str, int]
    ) -> Mapping[str, int]:
        if any(priority < 0 for priority in value.values()):
            raise ValueError("prioridades não podem ser negativas")
        return value


class PlanningStatistics(_FrozenModel):
    total_steps: int = Field(ge=0)
    dependency_count: int = Field(ge=0)
    maximum_depth: int = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    estimated_duration_seconds: float = Field(ge=0)
    memory_entries_considered: int = Field(ge=0)


class PlanningResult(_FrozenModel):
    plan: ExecutionPlan
    warnings: tuple[str, ...] = ()
    validation_messages: tuple[str, ...] = ()
    statistics: PlanningStatistics


__all__ = [
    "ExecutionPlan",
    "PlanningContext",
    "PlanningPolicy",
    "PlanningRequest",
    "PlanningResult",
    "PlanningStatistics",
    "PlanStep",
    "PlanStepStatus",
]

