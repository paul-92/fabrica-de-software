"""Read-only Application projection for effective runtime branding."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from asep.branding.models import DEFAULT_BRANDING_SETTINGS, BrandingSettings
from asep.branding.repository import BrandingRepository


class BrandingProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    product_name: str
    short_name: str
    logo_url: str | None
    workspace_label: str
    footer_text: str

    @classmethod
    def from_settings(cls, settings: BrandingSettings) -> BrandingProjection:
        return cls.model_validate(settings.model_dump(mode="python"))


class BrandingQueryService:
    def __init__(
        self,
        repository: BrandingRepository,
        defaults: BrandingSettings = DEFAULT_BRANDING_SETTINGS,
    ) -> None:
        self._repository = repository
        self._defaults = BrandingSettings.model_validate(
            defaults.model_dump(mode="python")
        )

    def get(self) -> BrandingProjection:
        effective = self._repository.get()
        return BrandingProjection.from_settings(
            self._defaults if effective is None else effective
        )


__all__ = ["BrandingProjection", "BrandingQueryService"]
