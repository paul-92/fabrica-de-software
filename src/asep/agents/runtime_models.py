"""Modelos estritos do runtime de agentes inteligentes."""

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
from asep.agents.contracts import (
    AgentCapability,
    AgentError,
    AgentId,
)
from asep.execution.models import AgentResult


class AgentExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class _FrozenRuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AgentExecutionPolicy(_FrozenRuntimeModel):
    timeout_seconds: float | None = Field(default=None, gt=0)
    max_attempts: int = Field(default=1, ge=1)
    retry_enabled: bool = False
    retry_unexpected_errors: bool = False
    validate_capability: bool = True
    fail_fast: bool = True

    @model_validator(mode="after")
    def retry_configuration_is_consistent(self) -> AgentExecutionPolicy:
        if not self.retry_enabled and self.max_attempts != 1:
            raise ValueError(
                "max_attempts deve ser 1 quando retry está desabilitado"
            )
        return self


class AgentExecutionRequest(_FrozenRuntimeModel):
    execution_id: str
    agent_id: AgentId
    capability: AgentCapability
    input: Mapping[str, JsonValue] = Field(
        default_factory=dict,
        repr=False,
    )
    context: Mapping[str, JsonValue] = Field(
        default_factory=dict,
        repr=False,
    )
    workflow_execution_id: str | None = None
    workflow_step_id: str | None = None
    correlation_id: str | None = None
    metadata: Mapping[str, JsonValue] = Field(
        default_factory=dict,
        repr=False,
    )
    timeout_seconds: float | None = Field(default=None, gt=0)
    cancellation_requested: bool = False

    @field_validator(
        "execution_id",
        "workflow_execution_id",
        "workflow_step_id",
        "correlation_id",
    )
    @classmethod
    def text_is_not_blank(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identificador não pode ser vazio")
        return value


class AgentExecutionContext(_FrozenRuntimeModel):
    execution_id: str
    agent_id: AgentId
    started_at: datetime
    workflow_execution_id: str | None = None
    workflow_step_id: str | None = None
    correlation_id: str | None = None
    metadata: Mapping[str, JsonValue] = Field(
        default_factory=dict,
        repr=False,
    )
    cancellation_requested: bool = False
    attempt: int = Field(default=1, ge=1)
    deadline: datetime | None = None

    @field_validator("started_at", "deadline")
    @classmethod
    def timestamps_are_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("timestamp deve possuir timezone")
        return value


class AgentExecutionResult(_FrozenRuntimeModel):
    execution_id: str
    agent_id: AgentId
    status: AgentExecutionStatus
    output: Mapping[str, Any] = Field(default_factory=dict, repr=False)
    started_at: datetime
    completed_at: datetime
    duration_seconds: float = Field(ge=0)
    attempts: int = Field(ge=0)
    error: AgentError | None = None
    metadata: Mapping[str, Any] = Field(default_factory=dict, repr=False)
    agent_result: AgentResult | None = Field(default=None, repr=False)

    @field_validator("started_at", "completed_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp deve possuir timezone")
        return value

    @field_validator("output", "metadata")
    @classmethod
    def mappings_are_json(
        cls,
        value: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return freeze_json(value, location="agent execution")

    @field_serializer("output", "metadata")
    def serialize_mappings(
        self,
        value: Mapping[str, Any],
    ) -> dict[str, Any]:
        return json_value(value)

    @model_validator(mode="after")
    def result_is_consistent(self) -> AgentExecutionResult:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at não pode preceder started_at")
        succeeded = self.status is AgentExecutionStatus.SUCCEEDED
        if succeeded and self.error is not None:
            raise ValueError("resultado succeeded não pode possuir erro")
        if not succeeded and self.error is None:
            raise ValueError("resultado não sucedido deve possuir erro")
        return self

    def __deepcopy__(
        self,
        memo: dict[int, Any],
    ) -> AgentExecutionResult:
        copied = AgentExecutionResult.model_validate(
            self.model_dump(mode="json")
        )
        memo[id(self)] = copied
        return copied
