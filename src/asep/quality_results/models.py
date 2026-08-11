"""Immutable structured facts produced by Quality Gate evaluation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from asep.execution.models import GateDecision, GateResult


class StoredQualityGateResult(BaseModel):
    """Canonical persisted representation of an evaluated Quality Gate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_id: str
    run_id: str
    stage_id: str
    decision: GateDecision
    satisfied_criteria: tuple[str, ...] = ()
    unsatisfied_criteria: tuple[str, ...] = ()
    evaluated_at: datetime

    @field_validator("gate_id", "run_id", "stage_id")
    @classmethod
    def identifiers_are_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identificadores de Quality Gate não podem ser vazios")
        return value

    @field_validator("satisfied_criteria", "unsatisfied_criteria")
    @classmethod
    def criteria_are_not_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not criterion.strip() for criterion in value):
            raise ValueError("critérios de Quality Gate não podem ser vazios")
        return value

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at deve possuir timezone")
        return value

    @classmethod
    def from_gate_result(cls, result: GateResult) -> StoredQualityGateResult:
        return cls.model_validate(result.model_dump(mode="json"))


__all__ = ["StoredQualityGateResult"]
