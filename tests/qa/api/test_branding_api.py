from __future__ import annotations

import ast
import inspect
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from asep.api import create_app, create_default_app
from asep.application import BrandingQueryService, RunQueryService
from asep.branding import (
    DEFAULT_BRANDING_SETTINGS,
    BrandingSettings,
    BrandingStorageReadError,
    InMemoryBrandingRepository,
)
from asep.configuration import ApplicationSettings, StorageBackend
from asep.metrics import MetricsService
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository

PATH = "/api/v1/branding"
PUBLIC_FIELDS = {
    "product_name",
    "short_name",
    "logo_url",
    "workspace_label",
    "footer_text",
}


def override(name: str = "Runtime Product") -> BrandingSettings:
    return BrandingSettings(
        product_name=name,
        short_name="RP",
        logo_url="https://cdn.example.com/runtime.svg",
        workspace_label="Runtime workspace",
        footer_text="Runtime footer",
    )


def client_for(service: object) -> TestClient:
    query = RunQueryService(InMemoryRunRepository(), InMemoryTimelineRepository())
    return TestClient(
        create_app(
            query,
            MetricsService(query),
            branding_query_service=service,  # type: ignore[arg-type]
        ),
        raise_server_exceptions=False,
    )


def test_get_serializes_complete_defaults_with_null_logo() -> None:
    response = client_for(
        BrandingQueryService(InMemoryBrandingRepository())
    ).get(PATH)
    assert response.status_code == 200
    assert response.json() == DEFAULT_BRANDING_SETTINGS.model_dump(mode="json")
    assert response.json()["logo_url"] is None
    assert set(response.json()) == PUBLIC_FIELDS


def test_get_serializes_complete_override_and_https_logo() -> None:
    repository = InMemoryBrandingRepository()
    repository.replace(override())
    response = client_for(BrandingQueryService(repository)).get(PATH)
    assert response.status_code == 200
    assert response.json() == override().model_dump(mode="json")
    assert response.json()["logo_url"].startswith("https://")


class FailingBrandingService:
    def get(self):
        raise BrandingStorageReadError(
            "private malformed SQLite payload",
            path=Path("C:/private/branding.db"),
        )


class UnexpectedFailingBrandingService:
    def get(self):
        raise RuntimeError("private implementation detail")


def test_storage_failure_is_safe_generic_500() -> None:
    response = client_for(FailingBrandingService()).get(PATH)
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "BRANDING_INTERNAL_ERROR",
            "message": "Branding could not be read.",
        }
    }
    for private in ("private", "sqlite", "payload", "branding.db", "C:"):
        assert private.casefold() not in response.text.casefold()


def test_unexpected_failure_is_safe_generic_500() -> None:
    response = client_for(UnexpectedFailingBrandingService()).get(PATH)
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error.",
        }
    }
    assert "private" not in response.text


def test_only_get_is_registered() -> None:
    client = client_for(BrandingQueryService(InMemoryBrandingRepository()))
    assert client.get(PATH).status_code == 200
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)(PATH).status_code == 405


def test_openapi_contract_is_exact_and_bounded() -> None:
    schema = client_for(
        BrandingQueryService(InMemoryBrandingRepository())
    ).app.openapi()
    operation = schema["paths"][PATH]["get"]
    properties = schema["components"]["schemas"]["BrandingResponse"]["properties"]

    assert set(schema["paths"][PATH]) == {"get"}
    assert set(operation["responses"]) == {"200", "500"}
    assert set(properties) == PUBLIC_FIELDS
    serialized = str(properties).casefold()
    for forbidden in (
        "version",
        "source",
        "storage",
        "backend",
        "path",
        "metadata",
        "theme",
        "color",
        "favicon",
    ):
        assert forbidden not in serialized


def test_default_app_exposes_defaults() -> None:
    response = TestClient(create_default_app(ApplicationSettings())).get(PATH)
    assert response.status_code == 200
    assert response.json() == DEFAULT_BRANDING_SETTINGS.model_dump(mode="json")


def test_default_app_observes_file_and_sqlite_persistence(tmp_path: Path) -> None:
    for settings in (
        ApplicationSettings(
            storage_backend=StorageBackend.FILE,
            storage_directory=tmp_path / "file",
        ),
        ApplicationSettings(
            storage_backend=StorageBackend.SQLITE,
            sqlite_database=tmp_path / "asep.db",
        ),
    ):
        from asep.repositories import RepositoryFactory

        canonical = RepositoryFactory(settings).create().branding_repository
        canonical.replace(override(settings.storage_backend.value))
        response = TestClient(create_default_app(settings)).get(PATH)
        assert response.json()["product_name"] == settings.storage_backend.value


def test_default_app_maps_malformed_sqlite_branding_to_safe_500(
    tmp_path: Path,
) -> None:
    database = tmp_path / "private-branding.db"
    settings = ApplicationSettings(
        storage_backend=StorageBackend.SQLITE,
        sqlite_database=database,
    )
    create_default_app(settings)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO branding_settings (id, version, payload) VALUES (?, ?, ?)",
            ("runtime", "1.0", "{private malformed payload"),
        )

    response = TestClient(
        create_default_app(settings), raise_server_exceptions=False
    ).get(PATH)
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "BRANDING_INTERNAL_ERROR",
            "message": "Branding could not be read.",
        }
    }
    assert "private" not in response.text.casefold()


def test_route_imports_only_api_application_and_fastapi() -> None:
    from asep.api import branding_routes

    imported = {
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(branding_routes)))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported <= {
        "fastapi",
        "asep.api.branding_schemas",
        "asep.api.routes",
        "asep.api.schemas",
        "asep.application",
    }
    assert not any(name.startswith((
        "asep.branding",
        "asep.repositories",
        "asep.sqlite",
        "pathlib",
    )) for name in imported)
