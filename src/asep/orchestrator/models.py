"""Modelos públicos do Intelligent Orchestrator."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
)

from asep.agents.coordination import CoordinationResult
from asep.business_engineering import (
    BusinessDescription,
    ProjectBlueprint,
)
from asep.execution.models import (
    ArtifactReference,
    GateResult,
)
from asep.planning import PlanningResult


class _FrozenModel(BaseModel):
    """Modelo-base imutável e estrito."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class IntelligentExecutionStatus(StrEnum):
    """Estados possíveis de uma execução inteligente."""

    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    PARTIAL = "partial"


class IntelligentExecutionRequest(_FrozenModel):
    """Entrada pública do pipeline inteligente."""

    run_id: str
    project_id: str
    project_name: str
    gate_id: str
    description: BusinessDescription
    artifacts_root: Path
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator(
        "run_id",
        "project_id",
        "project_name",
        "gate_id",
    )
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "identificador e nome do projeto não podem ser vazios"
            )

        return normalized


class IntelligentExecutionResult(_FrozenModel):
    """Resultado consolidado do pipeline inteligente."""

    run_id: str
    project_id: str
    status: IntelligentExecutionStatus
    blueprint: ProjectBlueprint | None = None
    planning_result: PlanningResult | None = None
    coordination_result: CoordinationResult | None = None
    artifact_references: tuple[ArtifactReference, ...] = ()
    gate_results: tuple[GateResult, ...] = ()
    errors: tuple[str, ...] = ()
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator(
        "run_id",
        "project_id",
    )
    @classmethod
    def identifiers_are_not_blank(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "identificadores da execução não podem ser vazios"
            )

        return normalized

    @field_validator("errors")
    @classmethod
    def errors_are_not_blank(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError(
                "mensagens de erro não podem ser vazias"
            )

        return value


__all__ = [
    "IntelligentExecutionRequest",
    "IntelligentExecutionResult",
    "IntelligentExecutionStatus",
]