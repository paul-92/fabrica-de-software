"""Trusted Application command for complete runtime branding replacement."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from asep.application.branding_query import BrandingProjection
from asep.branding.models import BrandingSettings
from asep.branding.repository import BrandingRepository


class BrandingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    product_name: str
    short_name: str
    logo_url: str | None
    workspace_label: str
    footer_text: str


class BrandingAdministrationService:
    def __init__(self, repository: BrandingRepository) -> None:
        self._repository = repository

    def replace(self, request: BrandingUpdateRequest) -> BrandingProjection:
        settings = BrandingSettings.model_validate(
            request.model_dump(mode="python")
        )
        self._repository.replace(settings)
        return BrandingProjection.from_settings(settings)


__all__ = ["BrandingAdministrationService", "BrandingUpdateRequest"]
