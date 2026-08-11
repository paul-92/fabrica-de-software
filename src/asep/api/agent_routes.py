"""Rota read-only do catÃ¡logo pÃºblico de agentes."""

from fastapi import APIRouter

from asep.api.agent_schemas import (
    AgentCatalogItemResponse,
    AgentCatalogListResponse,
    AgentRuntimeProjectionItemResponse,
    AgentRuntimeProjectionListResponse,
)
from asep.api.routes import API_PREFIX
from asep.api.schemas import ErrorResponse
from asep.application import AgentCatalogService, AgentRuntimeProjectionService


def create_agent_catalog_router(service: AgentCatalogService) -> APIRouter:
    router = APIRouter(prefix=f"{API_PREFIX}/agents", tags=["agents"])

    @router.get(
        "",
        response_model=AgentCatalogListResponse,
        responses={503: {"model": ErrorResponse}},
        summary="List public agent catalog",
    )
    def list_agents() -> AgentCatalogListResponse:
        return AgentCatalogListResponse(
            items=tuple(
                AgentCatalogItemResponse.from_application(item)
                for item in service.list_agents()
            )
        )

    return router


def create_agent_runtime_projection_router(
    service: AgentRuntimeProjectionService,
) -> APIRouter:
    router = APIRouter(prefix=f"{API_PREFIX}/agents", tags=["agents"])

    @router.get(
        "/runtime",
        response_model=AgentRuntimeProjectionListResponse,
        summary="List public agent runtime facts",
    )
    def list_agent_runtime_facts() -> AgentRuntimeProjectionListResponse:
        return AgentRuntimeProjectionListResponse(
            items=tuple(
                AgentRuntimeProjectionItemResponse.from_application(item)
                for item in service.list_agents()
            )
        )

    return router


__all__ = [
    "create_agent_catalog_router",
    "create_agent_runtime_projection_router",
]
