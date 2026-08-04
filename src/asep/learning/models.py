"""Modelos estruturados de conhecimento aprendido."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from asep._json_values import freeze_json
from asep.agents import AgentId
from asep.ai_planning import EngineeringReflection
from asep.memory import MemoryEntry, MemoryId
from asep.repair import RepairResult


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


class LearningRequest(BaseModel):
    """Entrada explícita da extração, adaptação e persistência."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repair_result: RepairResult
    reflection: EngineeringReflection
    source_execution_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    memory_id: MemoryId
    agent_id: AgentId
    execution_id: str = Field(min_length=1)
    workflow_execution_id: str | None = None
    created_at: datetime
    updated_at: datetime


class LearningResult(BaseModel):
    """Resultado estruturado do aprendizado persistido."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    learned_knowledge: LearnedKnowledge
    memory_entry: MemoryEntry


class KnowledgeRetrievalRequest(BaseModel):
    """Filtros explícitos para recuperar conhecimento aprendido."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: AgentId
    text: str | None = None
    max_results: int = Field(default=10, ge=1)
    source_type: str | None = None
    minimum_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("text", "source_type")
    @classmethod
    def optional_text_is_not_blank(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("filtro textual não pode ser vazio")
        return value


class LearnedKnowledgeContext(BaseModel):
    """Contexto recuperado sem reconstrução textual de LearnedKnowledge."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entries: tuple[MemoryEntry, ...] = ()
    total_matches: int = Field(ge=0)


__all__ = [
    "LearnedKnowledge",
    "LearnedKnowledgeContext",
    "KnowledgeRetrievalRequest",
    "LearningRequest",
    "LearningResult",
]
