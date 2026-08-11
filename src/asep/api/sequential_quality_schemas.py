"""Strict HTTP schemas for sequential Quality Gate results."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from asep.application import SequentialQualityGateProjection
from asep.execution.models import GateDecision


class SequentialQualityGateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_id: str
    execution_id: str
    stage_id: str
    decision: GateDecision
    satisfied_criteria: tuple[str, ...]
    unsatisfied_criteria: tuple[str, ...]
    evaluated_at: datetime


class SequentialQualityGateListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[SequentialQualityGateResponse, ...]

    @classmethod
    def from_application(
        cls,
        projection: SequentialQualityGateProjection,
    ) -> SequentialQualityGateListResponse:
        return cls(
            items=tuple(
                SequentialQualityGateResponse(
                    gate_id=result.gate_id,
                    execution_id=result.run_id,
                    stage_id=result.stage_id,
                    decision=result.decision,
                    satisfied_criteria=result.satisfied_criteria,
                    unsatisfied_criteria=result.unsatisfied_criteria,
                    evaluated_at=result.evaluated_at,
                )
                for result in projection.quality_gates
            )
        )


__all__ = [
    "SequentialQualityGateListResponse",
    "SequentialQualityGateResponse",
]
