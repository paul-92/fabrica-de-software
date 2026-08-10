"""Consulta pÃºblica e read-only do catÃ¡logo declarativo de agentes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class AgentCatalogEntry(BaseModel):
    """ProjeÃ§Ã£o segura; nÃ£o representa disponibilidade no runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str
    name: str
    version: str
    lifecycle_status: str
    department: str
    capabilities: tuple[str, ...] = ()

    @field_validator(
        "agent_id", "name", "version", "lifecycle_status", "department"
    )
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("agent catalog field must not be blank")
        return value

    @field_validator("capabilities")
    @classmethod
    def capabilities_are_not_blank(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("agent capability must not be blank")
        return value

    @model_validator(mode="after")
    def capabilities_are_unique(self) -> AgentCatalogEntry:
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("agent capabilities must be unique")
        return self


@runtime_checkable
class AgentCatalogSource(Protocol):
    """Porta estreita para uma fonte declarativa de agentes."""

    def list_agents(self) -> tuple[AgentCatalogEntry, ...]: ...


class AgentCatalogService:
    def __init__(self, source: AgentCatalogSource) -> None:
        self._source = source

    def list_agents(self) -> tuple[AgentCatalogEntry, ...]:
        return tuple(
            sorted(self._source.list_agents(), key=lambda item: item.agent_id)
        )


__all__ = ["AgentCatalogEntry", "AgentCatalogService", "AgentCatalogSource"]
