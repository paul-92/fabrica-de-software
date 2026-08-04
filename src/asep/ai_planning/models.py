"""Modelos estruturados para planejamento assistido de reparos."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


__all__ = ["RepairProposal"]

