from pathlib import Path
import os
import pytest
from fastapi.testclient import TestClient

from asep.api.composition import create_default_app
from asep.configuration import ApplicationSettings, Configuration, ConfigurationValidationError, EnvironmentMode, StorageBackend


def production(tmp_path: Path, **overrides):
    values = dict(
        environment="production", storage_backend="sqlite",
        sqlite_database=tmp_path / "database" / "asep.db",
        hosted_root=tmp_path / "workspaces",
        maintenance_directory=tmp_path / "maintenance",
        cors_origins=("https://beta.example",), access_cookie_secure=True,
        legacy_admin_email="admin@example.test",
        legacy_admin_password="strong-private-beta-password",
    )
    values.update(overrides)
    return ApplicationSettings(**values)


@pytest.fixture(autouse=True)
def non_temporary_root(monkeypatch, tmp_path):
    monkeypatch.setattr("asep.configuration.models.tempfile.gettempdir", lambda: str(tmp_path.parent / "different-temp"))


def test_development_defaults_remain_compatible():
    settings=Configuration.load({})
    assert settings.environment is EnvironmentMode.DEVELOPMENT
    assert settings.storage_backend is StorageBackend.MEMORY


def test_valid_production_starts_and_is_ready(tmp_path):
    settings=production(tmp_path)
    client=TestClient(create_default_app(settings))
    assert client.get("/api/v1/ready").json()=={"status":"ready"}
    assert settings.sqlite_database.parent.is_dir()
    assert settings.hosted_root.is_dir()


@pytest.mark.parametrize("updates",[
    {"storage_backend":"memory"},{"storage_backend":"file"},
    {"sqlite_database":"relative.db"},{"hosted_root":"relative-workspaces"},
    {"maintenance_directory":"relative-maintenance"},
    {"access_cookie_secure":False},{"legacy_admin_password":"change-me-local-admin"},
    {"legacy_admin_email":"invalid"},{"cors_origins":("http://beta.example",)},
    {"cors_origins":("https://localhost",)},{"cors_origins":("https://127.0.0.1",)},
])
def test_invalid_production_is_rejected(tmp_path, updates):
    with pytest.raises(ConfigurationValidationError): production(tmp_path,**updates)


def test_database_inside_hosted_root_is_rejected(tmp_path):
    with pytest.raises(ConfigurationValidationError):
        production(tmp_path,hosted_root=tmp_path/"root",sqlite_database=tmp_path/"root"/"db.sqlite")


def test_maintenance_is_disjoint_from_persistence(tmp_path):
    with pytest.raises(ConfigurationValidationError):
        production(tmp_path, hosted_root=tmp_path/"root", maintenance_directory=tmp_path/"root"/"maintenance")
    with pytest.raises(ConfigurationValidationError):
        production(tmp_path, maintenance_directory=tmp_path/"database")


def test_wildcard_cors_is_rejected(tmp_path):
    with pytest.raises(ConfigurationValidationError): production(tmp_path,cors_origins=("*",))


@pytest.mark.parametrize("field", ["sqlite_database", "hosted_root"])
def test_persistent_location_must_be_writable_directory(tmp_path, field):
    obstacle=tmp_path/"not-a-directory"
    obstacle.write_text("bounded",encoding="utf-8")
    value=obstacle/"asep.db" if field=="sqlite_database" else obstacle
    with pytest.raises(ConfigurationValidationError): production(tmp_path,**{field:value})


def test_next_public_values_are_not_backend_configuration():
    settings=Configuration.load({"NEXT_PUBLIC_ADMIN_PASSWORD":"must-not-be-read"})
    assert settings==ApplicationSettings()


def test_readiness_failure_is_bounded(tmp_path):
    settings=production(tmp_path); app=create_default_app(settings)
    settings.hosted_root.rmdir()
    response=TestClient(app).get("/api/v1/ready")
    assert response.status_code==503
    assert response.json()=={"status":"unavailable"}
    assert str(tmp_path) not in response.text


def test_production_admin_login_uses_existing_secure_cookie_contract(tmp_path):
    client=TestClient(create_default_app(production(tmp_path)),base_url="https://beta.example")
    response=client.post("/api/v1/access/login",json={"email":"admin@example.test","password":"strong-private-beta-password"})
    assert response.status_code==200
    cookie=response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
