"""Isolated in-memory runtime branding repository."""

from asep.branding.models import BrandingSettings
from asep.branding.serialization import BrandingCodec


class InMemoryBrandingRepository:
    def __init__(self) -> None:
        self._settings: BrandingSettings | None = None

    def get(self) -> BrandingSettings | None:
        return None if self._settings is None else self._copy(self._settings)

    def replace(self, settings: BrandingSettings) -> None:
        self._settings = self._copy(settings)

    @staticmethod
    def _copy(settings: BrandingSettings) -> BrandingSettings:
        return BrandingCodec.decode(BrandingCodec.encode(settings))


__all__ = ["InMemoryBrandingRepository"]
