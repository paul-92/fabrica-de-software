"""Read-only HTTP route for sequential Quality Gate results."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from asep.api.routes import API_PREFIX
from asep.api.schemas import ErrorResponse
from asep.api.sequential_quality_schemas import (
    SequentialQualityGateListResponse,
)
from asep.application import SequentialQualityGateQueryService

Identifier = Annotated[
    str,
    Path(min_length=1, pattern=r".*\S.*"),
]


def create_sequential_quality_router(
    service: SequentialQualityGateQueryService,
) -> APIRouter:
    router = APIRouter(
        prefix=f"{API_PREFIX}/sequential-projects",
        tags=["sequential-quality"],
    )

    @router.get(
        "/{project_id}/executions/{execution_id}/quality-gates",
        response_model=SequentialQualityGateListResponse,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        summary="List Quality Gate results for a sequential execution",
    )
    def list_quality_gates(
        project_id: Identifier,
        execution_id: Identifier,
    ) -> SequentialQualityGateListResponse:
        return SequentialQualityGateListResponse.from_application(
            service.get(project_id, execution_id)
        )

    return router


__all__ = ["create_sequential_quality_router"]
