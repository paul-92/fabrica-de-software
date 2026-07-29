"""Modelos estritos do motor de execução."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExecutionStatus(StrEnum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class StageStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class RunContext(BaseModel):
    """Identidade e paths imutáveis de uma execução."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    project_id: str
    workflow_id: str
    started_at: datetime
    resumed_at: datetime | None = None
    current_stage: str | None = None
    execution_status: ExecutionStatus
    project_path: Path
    state_path: Path
    artifacts_path: Path
    logs_path: Path

    @field_validator("run_id")
    @classmethod
    def run_id_is_uuid4(cls, value: str) -> str:
        from uuid import UUID

        parsed = UUID(value)
        if parsed.version != 4:
            raise ValueError("run_id deve ser UUID v4")
        return value


class TransitionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    run_id: str
    entity: str
    previous_state: str
    new_state: str
    reason: str
    component: str


class StageState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: StageStatus = StageStatus.PENDING
    agent_id: str
    quality_gate_id: str | None = None
    attempts: int = 0


class ExecutionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    project_id: str
    workflow_id: str
    execution_status: ExecutionStatus
    current_stage: str | None
    created_at: datetime
    updated_at: datetime
    resumed_at: datetime | None = None
    stages: list[StageState]
    transition_history: list[TransitionRecord] = Field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    artifact_references: list[dict[str, Any]] = Field(default_factory=list)


class ArtifactDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    type: str = "markdown"
    content: str


class ArtifactReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    run_id: str
    project_id: str
    stage_id: str
    agent_id: str
    path: str
    type: str
    created_at: datetime
    checksum: str


class AgentContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    project_id: str
    project_name: str
    workflow_id: str
    stage_id: str
    agent_id: str
    started_at: datetime
    objective: str | None
    scope_received: str | None
    constraints: tuple[str, ...] = ()
    pending_items: tuple[str, ...] = ()


class AgentResultStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"
    FAILED = "failed"


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AgentResultStatus
    agent_id: str
    stage_id: str
    run_id: str
    started_at: datetime
    finished_at: datetime
    artifacts: list[ArtifactDraft] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GateDecision(StrEnum):
    APPROVED = "APPROVED"
    APPROVED_WITH_PENDING = "APPROVED_WITH_PENDING"
    BLOCKED = "BLOCKED"


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_id: str
    run_id: str
    stage_id: str
    decision: GateDecision
    satisfied_criteria: list[str]
    unsatisfied_criteria: list[str]
    evaluated_at: datetime


class ExecutionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    project_id: str
    workflow_id: str
    status: ExecutionStatus
    current_stage: str | None
    state_path: Path
    artifacts_path: Path
    completed_stages: tuple[str, ...]
    messages: tuple[str, ...] = ()
