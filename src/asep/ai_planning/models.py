"""Modelos estruturados para planejamento assistido de reparos."""

from __future__ import annotations

from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.repair.models import (
    FailureAnalysis,
    RepairPlan,
    RepairResult,
    RepairStatus,
)


class RepairProposal(BaseModel):
    """Proposta informativa de reparo, sem conteúdo de código executável."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    summary: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    candidate_files: tuple[str, ...] = Field(min_length=1)
    suggested_actions: tuple[str, ...] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator(
        "summary",
        "reasoning",
    )
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("texto obrigatório não pode ser vazio")
        return value

    @field_validator(
        "candidate_files",
        "suggested_actions",
    )
    @classmethod
    def entries_are_not_blank(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("itens não podem ser vazios")
        return values


class EngineeringReflection(BaseModel):
    """Avaliação estruturada e não executável de um resultado de reparo."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    summary: str = Field(min_length=1)
    outcome: RepairStatus
    lessons: tuple[str, ...] = Field(min_length=1)
    recommended_actions: tuple[str, ...] = Field(min_length=1)
    should_retry: bool
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("outcome")
    @classmethod
    def outcome_is_supported(cls, value: RepairStatus) -> RepairStatus:
        supported = {
            RepairStatus.SUCCEEDED,
            RepairStatus.FAILED,
            RepairStatus.EXHAUSTED,
        }
        if value not in supported:
            raise ValueError("outcome deve ser terminal e refletível")
        return value

    @field_validator("summary")
    @classmethod
    def summary_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("summary não pode ser vazio")
        return value

    @field_validator("lessons", "recommended_actions")
    @classmethod
    def reflection_entries_are_not_blank(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("itens de reflexão não podem ser vazios")
        return values


class AutonomousEngineeringRequest(BaseModel):
    """Entrada explícita do pipeline autônomo de engenharia."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    analysis: FailureAnalysis
    replacement_contents: Mapping[str, str]
    test_paths: tuple[str, ...] = ("tests",)


class AutonomousEngineeringResult(BaseModel):
    """Resultado consolidado das etapas compostas pelo pipeline."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    proposal: RepairProposal
    plan: RepairPlan
    repair_result: RepairResult
    reflection: EngineeringReflection


__all__ = [
    "AutonomousEngineeringRequest",
    "AutonomousEngineeringResult",
    "EngineeringReflection",
    "RepairProposal",
]
