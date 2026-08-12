from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from asep.api import create_default_app
from asep.branding import BrandingSettings, InMemoryBrandingRepository
from asep.configuration import ApplicationSettings
from asep.repositories import RepositoryFactory

PATH = "/api/v1/branding"


def branded(name: str) -> BrandingSettings:
    return BrandingSettings(
        product_name=name,
        short_name="ID",
        logo_url=None,
        workspace_label="Workspace",
        footer_text="Footer",
    )


class ObservedBrandingRepository(InMemoryBrandingRepository):
    def __init__(self) -> None:
        super().__init__()
        self.get_calls = 0

    def get(self):
        self.get_calls += 1
        return super().get()


def test_default_composition_queries_exact_repository_from_bundle(monkeypatch) -> None:
    bundle = RepositoryFactory(ApplicationSettings()).create()
    observed = ObservedBrandingRepository()
    observed.replace(branded("Shared identity"))
    bundle = replace(bundle, branding_repository=observed)
    created = 0

    def create_once(factory):
        nonlocal created
        created += 1
        return bundle

    monkeypatch.setattr(RepositoryFactory, "create", create_once)
    response = TestClient(create_default_app(ApplicationSettings())).get(PATH)

    assert created == 1
    assert observed.get_calls == 1
    assert response.json()["product_name"] == "Shared identity"


def test_two_memory_compositions_remain_isolated(monkeypatch) -> None:
    first = RepositoryFactory(ApplicationSettings()).create()
    second = RepositoryFactory(ApplicationSettings()).create()
    first.branding_repository.replace(branded("First"))
    second.branding_repository.replace(branded("Second"))
    bundles = iter((first, second))

    monkeypatch.setattr(RepositoryFactory, "create", lambda factory: next(bundles))
    first_app = create_default_app(ApplicationSettings())
    second_app = create_default_app(ApplicationSettings())

    assert TestClient(first_app).get(PATH).json()["product_name"] == "First"
    assert TestClient(second_app).get(PATH).json()["product_name"] == "Second"
