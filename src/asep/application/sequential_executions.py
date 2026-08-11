"""Read-only Application projection for sequential executions."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from asep.errors import AsepError
from asep.execution.models import ExecutionState, ExecutionStatus, StageStatus
from asep.quality_results import (
    QualityGateResultRepository,
    StoredQualityGateResult,
)


class SequentialExecutionNotFoundError(AsepError):
    code = "SEQUENTIAL_EXECUTION_NOT_FOUND"
    category = "validation"
    exit_code = 2


class SequentialExecutionOwnershipError(AsepError):
    code = "SEQUENTIAL_EXECUTION_OWNERSHIP_MISMATCH"
    category = "conflict"
    exit_code = 6


class SequentialStageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: str
    agent_id: str
    gate_id: str | None
    status: StageStatus
    attempts: int = Field(ge=0)


class SequentialExecution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    project_id: str
    workflow_id: str
    status: ExecutionStatus
    current_stage: str | None
    created_at: datetime
    updated_at: datetime
    resumed_at: datetime | None
    stages: tuple[SequentialStageSummary, ...]

    @classmethod
    def from_state(cls, state: ExecutionState) -> SequentialExecution:
        return cls(
            execution_id=state.run_id,
            project_id=state.project_id,
            workflow_id=state.workflow_id,
            status=state.execution_status,
            current_stage=state.current_stage,
            created_at=state.created_at,
            updated_at=state.updated_at,
            resumed_at=state.resumed_at,
            stages=tuple(
                SequentialStageSummary(
                    stage_id=stage.id,
                    agent_id=stage.agent_id,
                    gate_id=stage.quality_gate_id,
                    status=stage.status,
                    attempts=stage.attempts,
                )
                for stage in state.stages
            ),
        )


@runtime_checkable
class SequentialExecutionSource(Protocol):
    def get(
        self,
        project_id: str,
        execution_id: str,
    ) -> SequentialExecution: ...


class SequentialQualityGateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution: SequentialExecution
    quality_gates: tuple[StoredQualityGateResult, ...] = ()


class SequentialQualityGateQueryService:
    def __init__(
        self,
        executions: SequentialExecutionSource,
        quality_gates: QualityGateResultRepository,
    ) -> None:
        self._executions = executions
        self._quality_gates = quality_gates

    def get(
        self,
        project_id: str,
        execution_id: str,
    ) -> SequentialQualityGateProjection:
        execution = self._executions.get(project_id, execution_id)
        quality_gates = self._quality_gates.list_by_run(
            execution.execution_id
        )
        return SequentialQualityGateProjection(
            execution=execution,
            quality_gates=quality_gates,
        )


__all__ = [
    "SequentialExecution",
    "SequentialExecutionNotFoundError",
    "SequentialExecutionOwnershipError",
    "SequentialExecutionSource",
    "SequentialQualityGateProjection",
    "SequentialQualityGateQueryService",
    "SequentialStageSummary",
]
