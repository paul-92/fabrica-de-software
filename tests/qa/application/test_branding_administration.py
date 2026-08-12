from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.application import (
    BrandingAdministrationService,
    BrandingProjection,
    BrandingQueryService,
    BrandingUpdateRequest,
)
from asep.branding import (
    BrandingRepository,
    FileBrandingRepository,
    InMemoryBrandingRepository,
    SQLiteBrandingRepository,
)


def request(name: str = "Trusted Product", **updates: object) -> BrandingUpdateRequest:
    values: dict[str, object] = {
        "product_name": name,
        "short_name": "TP",
        "logo_url": "https://cdn.example.com/logo.svg",
        "workspace_label": "Trusted workspace",
        "footer_text": "Trusted footer",
    }
    values.update(updates)
    return BrandingUpdateRequest.model_validate(values)


def repositories(tmp_path: Path) -> tuple[BrandingRepository, ...]:
    return (
        InMemoryBrandingRepository(),
        FileBrandingRepository(tmp_path / "branding.json"),
        SQLiteBrandingRepository(tmp_path / "branding.db"),
    )


def test_update_request_is_frozen_strict_and_forbids_extra_fields() -> None:
    update = request()
    with pytest.raises(ValidationError):
        update.product_name = "Changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        BrandingUpdateRequest.model_validate({**update.model_dump(), "extra": True})
    with pytest.raises(ValidationError):
        BrandingUpdateRequest.model_validate({**update.model_dump(), "product_name": 1})


@pytest.mark.parametrize(
    "updates",
    (
        {"product_name": " "},
        {"short_name": "x" * 13},
        {"workspace_label": "bad\nlabel"},
        {"footer_text": "x" * 201},
        {"logo_url": "http://example.com/logo.svg"},
    ),
)
def test_replace_delegates_semantic_validation_to_canonical_settings(
    updates: dict[str, object],
) -> None:
    repository = InMemoryBrandingRepository()
    administration = BrandingAdministrationService(repository)
    with pytest.raises(ValidationError):
        administration.replace(request(**updates))
    assert repository.get() is None


@pytest.mark.parametrize("index", range(3))
def test_complete_replace_query_visibility_and_second_replacement(
    tmp_path: Path, index: int
) -> None:
    repository = repositories(tmp_path)[index]
    administration = BrandingAdministrationService(repository)
    query = BrandingQueryService(repository)

    first_request = request("First")
    first = administration.replace(first_request)
    assert isinstance(first, BrandingProjection)
    assert first.model_dump() == first_request.model_dump()
    assert first is not first_request
    assert query.get() == first

    second_request = request(
        "Second",
        short_name="S2",
        logo_url=None,
        workspace_label="Second workspace",
        footer_text="Second footer",
    )
    second = administration.replace(second_request)
    assert query.get() == second
    assert second.model_dump() == second_request.model_dump()
    assert second.model_dump() != first.model_dump()


@pytest.mark.parametrize("kind", ("file", "sqlite"))
def test_file_and_sqlite_reconstruct_administrated_state(
    tmp_path: Path, kind: str
) -> None:
    path = tmp_path / ("branding.json" if kind == "file" else "branding.db")
    repository: BrandingRepository
    if kind == "file":
        repository = FileBrandingRepository(path)
    else:
        repository = SQLiteBrandingRepository(path)
    BrandingAdministrationService(repository).replace(request("Persisted"))

    reconstructed = (
        FileBrandingRepository(path)
        if kind == "file"
        else SQLiteBrandingRepository(path)
    )
    assert BrandingQueryService(reconstructed).get().product_name == "Persisted"


def test_application_command_has_no_transport_or_infrastructure_dependencies() -> None:
    import asep.application.branding_administration as module

    source = inspect.getsource(module)
    assert "BrandingRepository" in source
    for forbidden in (
        "FastAPI",
        "InMemoryBrandingRepository",
        "FileBrandingRepository",
        "SQLiteBrandingRepository",
        "sqlite3",
        "pathlib",
        "filesystem",
        "frontend",
        "app.state",
    ):
        assert forbidden not in source

