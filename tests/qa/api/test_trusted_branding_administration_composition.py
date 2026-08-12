from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from asep.api import (
    TrustedBrandingAdministrationComposition,
    create_default_app,
    create_trusted_branding_administration_composition,
)
from asep.application import BrandingUpdateRequest
from asep.configuration import ApplicationSettings, StorageBackend
from asep.branding import InMemoryBrandingRepository
from asep.repositories import RepositoryFactory

PATH = "/api/v1/branding"


def request(name: str) -> BrandingUpdateRequest:
    return BrandingUpdateRequest(
        product_name=name,
        short_name="TA",
        logo_url=None,
        workspace_label="Trusted workspace",
        footer_text="Trusted footer",
    )


class ObservedRepository(InMemoryBrandingRepository):
    def __init__(self) -> None:
        super().__init__()
        self.get_calls = 0
        self.replace_calls = 0

    def get(self):
        self.get_calls += 1
        return super().get()

    def replace(self, settings):
        self.replace_calls += 1
        return super().replace(settings)


def test_trusted_composition_is_frozen_and_shares_query_command_state() -> None:
    composition = create_trusted_branding_administration_composition(
        ApplicationSettings()
    )
    assert isinstance(composition, TrustedBrandingAdministrationComposition)

    returned = composition.branding_administration.replace(request("Shared"))
    response = TestClient(composition.app).get(PATH)
    assert response.status_code == 200
    assert response.json() == returned.model_dump(mode="json")

    with pytest.raises((AttributeError, TypeError)):
        composition.app = create_default_app()  # type: ignore[misc]


def test_factory_builds_once_and_both_services_use_exact_bundle_repository(
    monkeypatch,
) -> None:
    bundle = RepositoryFactory(ApplicationSettings()).create()
    observed = ObservedRepository()
    bundle = replace(bundle, branding_repository=observed)
    calls = 0

    def create_once(factory):
        nonlocal calls
        calls += 1
        return bundle

    monkeypatch.setattr(RepositoryFactory, "create", create_once)
    composition = create_trusted_branding_administration_composition(
        ApplicationSettings()
    )
    composition.branding_administration.replace(request("Exact identity"))
    response = TestClient(composition.app).get(PATH)

    assert calls == 1
    assert observed.replace_calls == 1
    assert observed.get_calls == 1
    assert response.json()["product_name"] == "Exact identity"


def test_two_trusted_memory_compositions_are_isolated() -> None:
    first = create_trusted_branding_administration_composition(ApplicationSettings())
    second = create_trusted_branding_administration_composition(ApplicationSettings())
    first.branding_administration.replace(request("First"))
    second.branding_administration.replace(request("Second"))

    assert TestClient(first.app).get(PATH).json()["product_name"] == "First"
    assert TestClient(second.app).get(PATH).json()["product_name"] == "Second"


@pytest.mark.parametrize("backend", (StorageBackend.FILE, StorageBackend.SQLITE))
def test_trusted_composition_persists_through_reconstruction(
    tmp_path, backend: StorageBackend
) -> None:
    settings = ApplicationSettings(
        storage_backend=backend,
        storage_directory=tmp_path / "storage",
        sqlite_database=tmp_path / "asep.db",
    )
    first = create_trusted_branding_administration_composition(settings)
    first.branding_administration.replace(request(backend.value))

    reconstructed = create_trusted_branding_administration_composition(settings)
    assert TestClient(reconstructed.app).get(PATH).json()["product_name"] == backend.value


def test_no_public_mutation_was_added_and_default_app_remains_compatible() -> None:
    trusted = create_trusted_branding_administration_composition(ApplicationSettings())
    client = TestClient(trusted.app)
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)(PATH).status_code == 405

    default = TestClient(create_default_app(ApplicationSettings()))
    assert default.get(PATH).status_code == 200
    for existing in ("/api/v1/health", "/api/v1/runs", "/api/v1/projects"):
        assert default.get(existing).status_code == 200
