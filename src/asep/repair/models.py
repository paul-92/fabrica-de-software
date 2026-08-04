"""Modelos imutáveis para análise e reparo controlado de software."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _FrozenRepairModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class RepairStatus(StrEnum):
    PENDING = "pending"
    ANALYZED = "analyzed"
    PLANNED = "planned"
    APPLYING = "applying"
    VALIDATING = "validating"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXHAUSTED = "exhausted"


class FailureAnalysis(_FrozenRepairModel):
    """Diagnóstico de uma falha funcional observada na validação."""

    summary: str = Field(min_length=1)
    failure_output: str = ""
    affected_paths: tuple[str, ...] = ()
    probable_cause: str | None = None


class RepairChange(_FrozenRepairModel):
    """Alteração individual proposta para reparar o software."""

    path: str = Field(min_length=1)
    content: str
    overwrite: bool = True
    reason: str = Field(min_length=1)


class RepairPlan(_FrozenRepairModel):
    """Plano explícito e auditável de alterações."""

    analysis: FailureAnalysis
    changes: tuple[RepairChange, ...] = Field(min_length=1)
    test_paths: tuple[str, ...] = ("tests",)


class RepairAttempt(_FrozenRepairModel):
    """Registro de uma tentativa de reparo."""

    attempt: int = Field(ge=1)
    plan: RepairPlan
    status: RepairStatus = RepairStatus.PENDING
    messages: tuple[str, ...] = ()


class RepairResult(_FrozenRepairModel):
    """Resultado consolidado do processo de reparo."""

    status: RepairStatus
    attempts: tuple[RepairAttempt, ...] = ()
    final_analysis: FailureAnalysis | None = None
    messages: tuple[str, ...] = ()


__all__ = [
    "FailureAnalysis",
    "RepairAttempt",
    "RepairChange",
    "RepairPlan",
    "RepairResult",
    "RepairStatus",
]