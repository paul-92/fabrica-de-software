"""Schemas HTTP da projeÃ§Ã£o pÃºblica de agentes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from asep.application import AgentCatalogEntry, AgentRuntimeProjection


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


class AgentRuntimeProjectionItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    registered: bool
    execution_count: int
    succeeded: int
    failed: int
    rejected: int
    cancelled: int
    timed_out: int
    retries: int

    @classmethod
    def from_application(
        cls, projection: AgentRuntimeProjection
    ) -> AgentRuntimeProjectionItemResponse:
        return cls.model_validate(projection.model_dump(mode="json"))


class AgentRuntimeProjectionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[AgentRuntimeProjectionItemResponse, ...]


__all__ = [
    "AgentCatalogItemResponse",
    "AgentCatalogListResponse",
    "AgentRuntimeProjectionItemResponse",
    "AgentRuntimeProjectionListResponse",
]
