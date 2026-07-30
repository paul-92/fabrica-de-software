"""Modelos imutáveis de supervisão e recuperação."""

from __future__ import annotations

from enum import StrEnum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from asep.agents.contracts import AgentId
from asep.agents.runtime_models import (
    AgentExecutionRequest,
    AgentExecutionResult,
)
from asep.memory.models import MemoryEntry
from asep.planning.models import ExecutionPlan


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SupervisedExecutionState(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    RETRYING = "retrying"
    RECOVERING = "recovering"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"

    @property
    def is_terminal(self) -> bool:
        return self in {
            self.SUCCEEDED,
            self.FAILED,
            self.CANCELLED,
            self.ROLLED_BACK,
        }


class FailureCategory(StrEnum):
    VALIDATION = "validation_failure"
    TOOL = "tool_failure"
    AGENT = "agent_failure"
    WORKFLOW = "workflow_failure"
    INFRASTRUCTURE = "infrastructure_failure"
    TIMEOUT = "timeout_failure"
    CONFIGURATION = "configuration_failure"
    UNEXPECTED = "unexpected_failure"


class RetryDecision(StrEnum):
    RETRY = "retry"
    DO_NOT_RETRY = "do_not_retry"
    LIMIT_EXCEEDED = "limit_exceeded"


class BackoffKind(StrEnum):
    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class FallbackAction(StrEnum):
    FAIL = "fail"
    IGNORE_STEP = "ignore_step"
    CANCEL_WORKFLOW = "cancel_workflow"
    SUBSTITUTE_AGENT = "substitute_agent"
    ALTERNATIVE_STEP = "alternative_step"


class RetryPolicy(_FrozenModel):
    max_attempts: int = Field(default=1, ge=1, le=100)
    interval_seconds: float = Field(default=0, ge=0)
    backoff: BackoffKind = BackoffKind.CONSTANT
    eligible_failures: tuple[FailureCategory, ...] = (
        FailureCategory.AGENT,
        FailureCategory.TOOL,
        FailureCategory.INFRASTRUCTURE,
        FailureCategory.TIMEOUT,
    )
    max_delay_seconds: float | None = Field(default=None, ge=0)

    def decide(
        self, category: FailureCategory, attempts: int
    ) -> RetryDecision:
        if attempts >= self.max_attempts:
            return RetryDecision.LIMIT_EXCEEDED
        if category not in self.eligible_failures:
            return RetryDecision.DO_NOT_RETRY
        return RetryDecision.RETRY


class FallbackPolicy(_FrozenModel):
    action: FallbackAction = FallbackAction.FAIL
    replacement_agent_id: AgentId | None = None
    alternative_capability: str | None = None

    @model_validator(mode="after")
    def action_has_required_target(self) -> FallbackPolicy:
        if (
            self.action is FallbackAction.SUBSTITUTE_AGENT
            and self.replacement_agent_id is None
        ):
            raise ValueError(
                "substitute_agent exige replacement_agent_id"
            )
        if (
            self.action is FallbackAction.ALTERNATIVE_STEP
            and not self.alternative_capability
        ):
            raise ValueError(
                "alternative_step exige alternative_capability"
            )
        return self


class RecoveryPolicy(_FrozenModel):
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    fallback: FallbackPolicy = Field(default_factory=FallbackPolicy)


class RecoveryContext(_FrozenModel):
    request: AgentExecutionRequest
    execution_plan: ExecutionPlan | None = None
    workflow: Mapping[str, JsonValue] = Field(default_factory=dict)
    agent_id: AgentId | None = None
    memory: tuple[MemoryEntry, ...] = ()
    error: str | None = None
    attempts: int = Field(default=0, ge=0)
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)


class RecoveryResult(_FrozenModel):
    final_state: SupervisedExecutionState
    actions: tuple[str, ...]
    attempts: int = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    messages: tuple[str, ...] = ()
    category: FailureCategory | None = None
    execution_result: AgentExecutionResult | None = None


__all__ = [
    "BackoffKind",
    "FailureCategory",
    "FallbackAction",
    "FallbackPolicy",
    "RecoveryContext",
    "RecoveryPolicy",
    "RecoveryResult",
    "RetryDecision",
    "RetryPolicy",
    "SupervisedExecutionState",
]
