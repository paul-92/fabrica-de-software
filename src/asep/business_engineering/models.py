"""Modelos imutáveis da camada de Business Engineering."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _FrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class RequirementPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Requirement(_FrozenModel):
    id: str
    title: str
    description: str
    priority: RequirementPriority = RequirementPriority.MEDIUM
    functional: bool = True

    @field_validator("id", "title", "description")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório não pode ser vazio")
        return value

class Actor(_FrozenModel):
    id: str
    name: str
    description: str | None = None

    @field_validator("id", "name")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório não pode ser vazio")
        return value

class UseCase(_FrozenModel):
    id: str
    name: str
    description: str
    primary_actor_id: str
    requirement_ids: tuple[str, ...] = ()

    @field_validator(
        "id",
        "name",
        "description",
        "primary_actor_id",
    )
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório não pode ser vazio")
        return value 

class ProjectBlueprint(_FrozenModel):
    project_name: str
    description: str
    requirements: tuple[Requirement, ...] = ()
    actors: tuple[Actor, ...] = ()
    use_cases: tuple[UseCase, ...] = ()

    @field_validator("project_name", "description")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório não pode ser vazio")
        return value               

__all__ = [
    "Actor",
    "ProjectBlueprint",
    "Requirement",
    "RequirementPriority",
    "UseCase",
]