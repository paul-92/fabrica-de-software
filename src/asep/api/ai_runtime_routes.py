"""Rotas finas para status de AI Runtime."""

from fastapi import APIRouter, HTTPException

from asep.api.ai_runtime_schemas import (
    AIRuntimeListResponse,
    AIRuntimeStatusResponse,
)
from asep.api.routes import API_PREFIX
from asep.application import AIRuntimeConnectionService


def create_ai_runtime_router(
    service: AIRuntimeConnectionService,
) -> APIRouter:
    router = APIRouter(prefix=f"{API_PREFIX}/ai-runtimes", tags=["ai-runtimes"])

    @router.get("", response_model=AIRuntimeListResponse)
    def list_runtimes() -> AIRuntimeListResponse:
        return AIRuntimeListResponse(
            items=tuple(
                AIRuntimeStatusResponse.from_domain(status)
                for status in service.list_statuses()
            )
        )

    @router.get("/{runtime_id}/status", response_model=AIRuntimeStatusResponse)
    def get_runtime_status(runtime_id: str) -> AIRuntimeStatusResponse:
        try:
            status = service.get_status(runtime_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return AIRuntimeStatusResponse.from_domain(status)

    return router


__all__ = ["create_ai_runtime_router"]
