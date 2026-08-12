"""Public HTTP schema for effective runtime branding."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from asep.application import BrandingProjection


class BrandingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    product_name: str
    short_name: str
    logo_url: str | None
    workspace_label: str
    footer_text: str

    @classmethod
    def from_application(cls, projection: BrandingProjection) -> BrandingResponse:
        return cls.model_validate(projection.model_dump(mode="python"))


__all__ = ["BrandingResponse"]
