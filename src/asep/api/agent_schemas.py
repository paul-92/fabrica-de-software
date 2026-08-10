"""Schemas HTTP da projeÃ§Ã£o pÃºblica de agentes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from asep.application import AgentCatalogEntry


class AgentCatalogItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    name: str
    version: str
    lifecycle_status: str
    department: str
    capabilities: tuple[str, ...]

    @classmethod
    def from_application(
        cls, entry: AgentCatalogEntry
    ) -> AgentCatalogItemResponse:
        return cls.model_validate(entry.model_dump(mode="json"))


class AgentCatalogListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[AgentCatalogItemResponse, ...]


__all__ = ["AgentCatalogItemResponse", "AgentCatalogListResponse"]
