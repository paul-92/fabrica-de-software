"""Persistence port for the singleton runtime branding override."""

from typing import Protocol, runtime_checkable

from asep.branding.models import BrandingSettings


@runtime_checkable
class BrandingRepository(Protocol):
    def get(self) -> BrandingSettings | None: ...

    def replace(self, settings: BrandingSettings) -> None: ...


__all__ = ["BrandingRepository"]
