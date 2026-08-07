from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asep.api import create_default_app
from asep.configuration import (
    ApplicationSettings,
    Configuration,
    ConfigurationValidationError,
    StorageBackend,
)
from asep.repositories import RepositoryFactory
from asep.runs import FileRunRepository
from asep.timeline import FileTimelineRepository


def test_default_configuration_is_complete_and_immutable() -> None:
    settings = Configuration.load({})

    assert settings == ApplicationSettings(
        storage_backend=StorageBackend.MEMORY,
        storage_directory=Path("storage"),
        runs_filename="runs.json",
        timeline_filename="timeline-events.json",
        sqlite_database=Path("storage/asep.db"),
    )
    with pytest.raises(FrozenInstanceError):
        settings.runs_filename = "other.json"  # type: ignore[misc]


def test_configuration_reads_all_supported_environment_variables() -> None:
    settings = Configuration.load(
        {
            "ASEP_STORAGE_BACKEND": "file",
            "ASEP_STORAGE_DIRECTORY": "custom-storage",
            "ASEP_RUNS_FILENAME": "custom-runs.json",
            "ASEP_TIMELINE_FILENAME": "custom-timeline.json",
            "ASEP_SQLITE_DATABASE": "database/custom.db",
            "IGNORED": "value",
        }
    )

    assert settings.storage_backend is StorageBackend.FILE
    assert settings.storage_directory == Path("custom-storage")
    assert settings.runs_filename == "custom-runs.json"
    assert settings.timeline_filename == "custom-timeline.json"
    assert settings.sqlite_database == Path("database/custom.db")


def test_configuration_selects_sqlite_from_environment() -> None:
    settings = Configuration.load(
        {
            "ASEP_STORAGE_BACKEND": "sqlite",
            "ASEP_SQLITE_DATABASE": "custom/asep.db",
        }
    )

    assert settings.storage_backend is StorageBackend.SQLITE
    assert settings.sqlite_database == Path("custom/asep.db")


@pytest.mark.parametrize("backend", ["postgres", "", "FILE"])
def test_configuration_rejects_invalid_backend(backend: str) -> None:
    with pytest.raises(
        ConfigurationValidationError,
        match="não suportado",
    ):
        Configuration.load({"ASEP_STORAGE_BACKEND": backend})


@pytest.mark.parametrize("directory", ["", "   "])
def test_configuration_rejects_empty_directory(directory: str) -> None:
    with pytest.raises(
        ConfigurationValidationError,
        match="não pode ser vazio",
    ):
        ApplicationSettings(storage_directory=directory)


def test_configuration_rejects_empty_sqlite_database() -> None:
    with pytest.raises(
        ConfigurationValidationError,
        match="sqlite_database",
    ):
        ApplicationSettings(sqlite_database="")


def test_repair_workspace_is_optional() -> None:
    assert Configuration.load({}).repair_workspace is None


def test_repair_workspace_is_loaded_and_resolved(tmp_path: Path) -> None:
    settings = Configuration.load(
        {"ASEP_REPAIR_WORKSPACE": str(tmp_path)}
    )
    assert settings.repair_workspace == tmp_path.resolve()


@pytest.mark.parametrize("workspace", ["", "   "])
def test_repair_workspace_rejects_empty_value(workspace: str) -> None:
    with pytest.raises(ConfigurationValidationError, match="não pode ser vazio"):
        Configuration.load({"ASEP_REPAIR_WORKSPACE": workspace})


def test_repair_workspace_must_be_an_existing_directory(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigurationValidationError, match="deve existir"):
        ApplicationSettings(repair_workspace=tmp_path / "missing")


@pytest.mark.parametrize(
    ("field", "filename"),
    [
        ("runs_filename", ""),
        ("runs_filename", "nested/runs.json"),
        ("runs_filename", r"nested\runs.json"),
        ("runs_filename", ".."),
        ("timeline_filename", " "),
        ("timeline_filename", "/timeline.json"),
        ("timeline_filename", r"C:\timeline.json"),
        ("timeline_filename", "."),
    ],
)
def test_configuration_rejects_invalid_filenames(
    field: str,
    filename: str,
) -> None:
    with pytest.raises(
        ConfigurationValidationError,
        match=field,
    ):
        ApplicationSettings(**{field: filename})


def test_factory_uses_custom_file_configuration(tmp_path: Path) -> None:
    settings = ApplicationSettings(
        storage_backend="file",
        storage_directory=tmp_path,
        runs_filename="history.json",
        timeline_filename="events.json",
    )

    repositories = RepositoryFactory(settings).create()

    assert isinstance(repositories.run_repository, FileRunRepository)
    assert isinstance(
        repositories.timeline_repository,
        FileTimelineRepository,
    )
    assert (tmp_path / "history.json").exists()
    assert not (tmp_path / "runs.json").exists()


def test_dashboard_composition_uses_environment_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ASEP_STORAGE_BACKEND", "file")
    monkeypatch.setenv("ASEP_STORAGE_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("ASEP_RUNS_FILENAME", "dashboard-runs.json")
    monkeypatch.setenv(
        "ASEP_TIMELINE_FILENAME",
        "dashboard-timeline.json",
    )

    app = create_default_app()

    assert TestClient(app).get("/api/v1/runs").json() == {"items": []}
    assert (tmp_path / "dashboard-runs.json").exists()
    assert not (tmp_path / "runs.json").exists()


def test_configuration_public_exports_are_intentional() -> None:
    import asep.configuration as configuration

    assert set(configuration.__all__) == {
        "ApplicationSettings",
        "Configuration",
        "ConfigurationValidationError",
        "StorageBackend",
    }
