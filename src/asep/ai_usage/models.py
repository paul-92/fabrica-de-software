from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AIUsageOperation(StrEnum):
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    REPAIR = "repair"
    OTHER = "other"


class AIUsageStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AIUsageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    usage_id: str
    organization_id: str
    user_id: str
    project_id: str
    session_id: str
    execution_id: str
    runtime_id: str
    provider: str
    model: str | None = None
    operation: AIUsageOperation
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    provider_request_id: str | None = None
    started_at: datetime
    completed_at: datetime
    status: AIUsageStatus

    @model_validator(mode="after")
    def total_consistent(self):
        if self.input_tokens is not None and self.output_tokens is not None:
            expected = self.input_tokens + self.output_tokens
            if self.total_tokens is not None and self.total_tokens != expected:
                raise ValueError("total_tokens must equal input_tokens + output_tokens")
        return self


class AIUsageAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    calls: int
    known_input_tokens: int
    known_output_tokens: int
    known_total_tokens: int
    calls_with_unknown_usage: int

