"""Explicit versioned codec for runtime branding storage."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import ValidationError

from asep.branding.errors import (
    InvalidBrandingStorageFormatError,
    UnsupportedBrandingStorageVersionError,
)
from asep.branding.models import BrandingSettings

BRANDING_STORAGE_VERSION = "1.0"


class BrandingCodec:
    @staticmethod
    def encode(settings: BrandingSettings) -> dict[str, Any]:
        return settings.model_dump(mode="json")

    @staticmethod
    def decode(data: Mapping[str, Any]) -> BrandingSettings:
        try:
            return BrandingSettings.model_validate(data)
        except (TypeError, ValidationError) as exc:
            raise InvalidBrandingStorageFormatError(
                "Branding persistido possui formato inválido."
            ) from exc

    @classmethod
    def encode_document(cls, settings: BrandingSettings) -> dict[str, Any]:
        return {
            "version": BRANDING_STORAGE_VERSION,
            "branding": cls.encode(settings),
        }

    @classmethod
    def decode_document(cls, document: object) -> BrandingSettings:
        if not isinstance(document, dict) or set(document) != {"version", "branding"}:
            raise InvalidBrandingStorageFormatError(
                "Envelope de branding persistido possui formato inválido."
            )
        if document["version"] != BRANDING_STORAGE_VERSION:
            raise UnsupportedBrandingStorageVersionError(
                "Versão do branding persistido não é suportada."
            )
        branding = document["branding"]
        if not isinstance(branding, dict):
            raise InvalidBrandingStorageFormatError(
                "Payload de branding persistido deve ser um objeto."
            )
        return cls.decode(branding)


__all__ = ["BRANDING_STORAGE_VERSION", "BrandingCodec"]
