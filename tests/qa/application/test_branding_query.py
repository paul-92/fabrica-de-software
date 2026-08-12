from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.application import BrandingProjection, BrandingQueryService
from asep.branding import (
    DEFAULT_BRANDING_SETTINGS,
    BrandingRepository,
    BrandingSettings,
    FileBrandingRepository,
    InMemoryBrandingRepository,
    SQLiteBrandingRepository,
)


def configured(name: str = "Configured") -> BrandingSettings:
    return BrandingSettings(
        product_name=name,
        short_name="CFG",
        logo_url="https://cdn.example.com/logo.svg",
        workspace_label="Configured workspace",
        footer_text="Configured footer",
    )


def test_empty_repository_returns_detached_defaults_without_persisting() -> None:
    repository = InMemoryBrandingRepository()
    projection = BrandingQueryService(repository).get()

    assert projection == BrandingProjection.model_validate(
        DEFAULT_BRANDING_SETTINGS.model_dump()
    )
    assert projection is not DEFAULT_BRANDING_SETTINGS
    assert repository.get() is None


def test_complete_override_is_projected_without_field_merge() -> None:
    repository = InMemoryBrandingRepository()
    override = configured()
    repository.replace(override)

    projection = BrandingQueryService(repository).get()
    assert projection.model_dump() == override.model_dump()
    assert projection.product_name != DEFAULT_BRANDING_SETTINGS.product_name
    assert projection.workspace_label != DEFAULT_BRANDING_SETTINGS.workspace_label
    assert projection is not override


def test_projection_is_frozen_strict_and_forbids_extra_fields() -> None:
    projection = BrandingProjection.model_validate(configured().model_dump())
    with pytest.raises(ValidationError):
        projection.product_name = "Changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        BrandingProjection.model_validate({**projection.model_dump(), "extra": True})
    with pytest.raises(ValidationError):
        BrandingProjection.model_validate({**projection.model_dump(), "product_name": 1})


@pytest.mark.parametrize("kind", ("memory", "file", "sqlite"))
def test_application_observes_reconstructed_repository_backends(
    tmp_path: Path, kind: str
) -> None:
    if kind == "memory":
        repository: BrandingRepository = InMemoryBrandingRepository()
    elif kind == "file":
        path = tmp_path / "branding.json"
        FileBrandingRepository(path).replace(configured())
        repository = FileBrandingRepository(path)
    else:
        path = tmp_path / "branding.db"
        SQLiteBrandingRepository(path).replace(configured())
        repository = SQLiteBrandingRepository(path)
    if kind == "memory":
        repository.replace(configured())

    assert BrandingQueryService(repository).get().product_name == "Configured"


def test_service_depends_only_on_branding_protocol_and_models() -> None:
    import asep.application.branding_query as module

    source = inspect.getsource(module)
    assert "BrandingRepository" in source
    for forbidden in (
        "InMemoryBrandingRepository",
        "FileBrandingRepository",
        "SQLiteBrandingRepository",
        "FastAPI",
        "sqlite3",
        "pathlib",
        "frontend",
    ):
        assert forbidden not in source

