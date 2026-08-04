"""Modelos estruturados de conhecimento aprendido."""

from __future__ import annotations

from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from asep._json_values import freeze_json


class LearnedKnowledge(BaseModel):
    """Conhecimento reutilizável extraído, ainda não persistido."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    summary: str = Field(min_length=1)
    lessons: tuple[str, ...] = Field(min_length=1)
    recommended_actions: tuple[str, ...] = Field(min_length=1)
    source_execution_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator("summary", "source_execution_id", "source_type")
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("texto obrigatório não pode ser vazio")
        return value

    @field_validator("lessons", "recommended_actions")
    @classmethod
    def entries_are_not_blank(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("itens de conhecimento não podem ser vazios")
        return values

    @field_validator("metadata")
    @classmethod
    def metadata_is_json(
        cls,
        value: Mapping[str, JsonValue],
    ) -> Mapping[str, JsonValue]:
        return freeze_json(value, location="learned knowledge metadata")


__all__ = ["LearnedKnowledge"]

