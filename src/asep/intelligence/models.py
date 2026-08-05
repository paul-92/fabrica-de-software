"""Modelos somente leitura para contexto enriquecido por conhecimento."""

from __future__ import annotations

from typing import Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from asep._json_values import freeze_json
from asep.memory import MemoryEntry


class KnowledgeAwareContext(BaseModel):
    """Contexto base combinado com memórias aprendidas já recuperadas."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    base_context: Mapping[str, JsonValue] = Field(default_factory=dict)
    learned_entries: tuple[MemoryEntry, ...] = ()
    knowledge_count: int = Field(ge=0)
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator("base_context", "metadata")
    @classmethod
    def mappings_are_json(
        cls,
        value: Mapping[str, JsonValue],
    ) -> Mapping[str, JsonValue]:
        return freeze_json(value, location="knowledge-aware context")

    @model_validator(mode="after")
    def count_matches_entries(self) -> KnowledgeAwareContext:
        if self.knowledge_count != len(self.learned_entries):
            raise ValueError(
                "knowledge_count deve corresponder às entradas aprendidas"
            )
        return self


__all__ = ["KnowledgeAwareContext"]

