"""Router HTTP fino para Intelligent Engineering."""

from __future__ import annotations

from fastapi import APIRouter

from asep.api.intelligent_engineering_schemas import (
    IntelligentEngineeringExecuteRequest,
    IntelligentEngineeringExecuteResponse,
)
from asep.api.schemas import ErrorResponse
from asep.application import IntelligentEngineeringApplicationService


def create_intelligent_engineering_router(
    service: IntelligentEngineeringApplicationService,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/intelligent-engineering",
        tags=["intelligent-engineering"],
    )

    @router.post(
        "/execute",
        response_model=IntelligentEngineeringExecuteResponse,
        responses={
            400: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        summary="Execute intelligent engineering",
    )
    def execute(
        body: IntelligentEngineeringExecuteRequest,
    ) -> IntelligentEngineeringExecuteResponse:
        result = service.execute(body.to_application())
        return IntelligentEngineeringExecuteResponse.from_application(result)

    return router


__all__ = ["create_intelligent_engineering_router"]
