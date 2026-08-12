"""Canonical runtime branding model and defaults."""

from __future__ import annotations

import unicodedata
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator


class BrandingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    product_name: str
    short_name: str
    logo_url: str | None = None
    workspace_label: str
    footer_text: str

    @field_validator("product_name")
    @classmethod
    def product_name_is_valid(cls, value: str) -> str:
        return _validated_text(value, field="product_name", maximum=120)

    @field_validator("short_name")
    @classmethod
    def short_name_is_valid(cls, value: str) -> str:
        return _validated_text(value, field="short_name", maximum=12)

    @field_validator("workspace_label")
    @classmethod
    def workspace_label_is_valid(cls, value: str) -> str:
        return _validated_text(value, field="workspace_label", maximum=80)

    @field_validator("footer_text")
    @classmethod
    def footer_text_is_valid(cls, value: str) -> str:
        return _validated_text(value, field="footer_text", maximum=200)

    @field_validator("logo_url")
    @classmethod
    def logo_url_is_safe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if _has_control(value):
            raise ValueError("logo_url must be a valid HTTPS URL")
        normalized = value.strip()
        if not normalized or len(normalized) > 2048:
            raise ValueError("logo_url must be a valid HTTPS URL")
        parsed = urlsplit(normalized)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.netloc
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or "#" in normalized
        ):
            raise ValueError("logo_url must be an absolute HTTPS URL without credentials or fragment")
        return normalized


def _validated_text(value: str, *, field: str, maximum: int) -> str:
    if _has_control(value):
        raise ValueError(f"{field} must not contain control characters")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} must not be blank")
    if len(normalized) > maximum:
        raise ValueError(f"{field} must contain at most {maximum} characters")
    return normalized


def _has_control(value: str) -> bool:
    return any(unicodedata.category(character) == "Cc" for character in value)


DEFAULT_BRANDING_SETTINGS = BrandingSettings(
    product_name="Engineering Platform",
    short_name="EP",
    logo_url=None,
    workspace_label="Área de trabalho",
    footer_text="Engenharia com segurança",
)


__all__ = ["BrandingSettings", "DEFAULT_BRANDING_SETTINGS"]
