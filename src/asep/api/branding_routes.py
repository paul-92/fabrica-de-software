"""Read-only public runtime branding route."""

from fastapi import APIRouter

from asep.api.branding_schemas import BrandingResponse
from asep.api.routes import API_PREFIX
from asep.api.schemas import ErrorResponse
from asep.application import BrandingQueryService


def create_branding_router(service: BrandingQueryService) -> APIRouter:
    router = APIRouter(prefix=f"{API_PREFIX}/branding", tags=["branding"])

    @router.get(
        "",
        response_model=BrandingResponse,
        responses={500: {"model": ErrorResponse}},
        summary="Get effective runtime branding",
    )
    def get_branding() -> BrandingResponse:
        return BrandingResponse.from_application(service.get())

    return router


__all__ = ["create_branding_router"]
