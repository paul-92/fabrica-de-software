from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import asep
from asep.api import create_app, create_default_app
from asep.application import RunQueryService
from asep.metrics import MetricsService
from asep.repositories import (
    RepositoryConfigurationError,
    RepositoryFactory,
    RepositorySettings,
    StorageBackend,
)
from asep.runs import (
    FileRunRepository,
    InMemoryRunRepository,
    Run,
    RunRepository,
    RunStatus,
    SQLiteRunRepository,
)
from asep.timeline import (
    FileTimelineRepository,
    InMemoryTimelineRepository,
    TimelineEvent,
    TimelineEventType,
    TimelineRepository,
    SQLiteTimelineRepository,
)
from asep.quality_results import (
    FileQualityGateResultRepository,
    InMemoryQualityGateResultRepository,
    QualityGateResultRepository,
    SQLiteQualityGateResultRepository,
)
from asep.branding import (
    FileBrandingRepository,
    InMemoryBrandingRepository,
    SQLiteBrandingRepository,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def test_default_settings_select_memory() -> None:
    settings = RepositorySettings()

    assert settings.storage_backend is StorageBackend.MEMORY
    assert settings.storage_directory == Path("storage")


def test_factory_creates_memory_repositories() -> None:
    repositories = RepositoryFactory(RepositorySettings()).create()

    assert isinstance(
        repositories.run_repository,
        InMemoryRunRepository,
    )
    assert isinstance(
        repositories.timeline_repository,
        InMemoryTimelineRepository,
    )
    assert isinstance(repositories.run_repository, RunRepository)
    assert isinstance(
        repositories.timeline_repository,
        TimelineRepository,
    )
    assert isinstance(
        repositories.quality_gate_result_repository,
        InMemoryQualityGateResultRepository,
    )
    assert isinstance(
        repositories.branding_repository,
        InMemoryBrandingRepository,
    )
    assert isinstance(
        repositories.quality_gate_result_repository,
        QualityGateResultRepository,
    )


def test_factory_creates_file_repositories_at_stable_paths(
    tmp_path: Path,
) -> None:
    repositories = RepositoryFactory(
        RepositorySettings(
            storage_backend=StorageBackend.FILE,
            storage_directory=tmp_path / "storage",
        )
    ).create()

    assert isinstance(repositories.run_repository, FileRunRepository)
    assert isinstance(
        repositories.timeline_repository,
        FileTimelineRepository,
    )
    assert (tmp_path / "storage/runs.json").exists()
    assert isinstance(
        repositories.quality_gate_result_repository,
        FileQualityGateResultRepository,
    )
    assert isinstance(repositories.branding_repository, FileBrandingRepository)
    assert (tmp_path / "storage/quality-gate-results.json").exists()
    repositories.timeline_repository.append(
        TimelineEvent(
            id="event",
            run_id="run",
            timestamp=NOW,
            type=TimelineEventType.RUN_STARTED,
        )
    )
    assert (tmp_path / "storage/timeline-events.json").exists()


def test_string_backend_and_path_are_normalized(tmp_path: Path) -> None:
    settings = RepositorySettings(
        storage_backend="file",
        storage_directory=str(tmp_path),
    )

    assert settings.storage_backend is StorageBackend.FILE
    assert settings.storage_directory == tmp_path


@pytest.mark.parametrize("backend", ["postgres", "", "FILE"])
def test_unknown_backend_is_clear(backend: str) -> None:
    with pytest.raises(
        RepositoryConfigurationError,
        match="não suportado",
    ):
        RepositorySettings(
            storage_backend=backend,
        )


def test_file_backend_rejects_empty_storage_directory() -> None:
    with pytest.raises(
        RepositoryConfigurationError,
        match="storage_directory",
    ):
        RepositorySettings(
            storage_backend=StorageBackend.FILE,
            storage_directory="",
        )


def test_factory_calls_return_isolated_repository_sets() -> None:
    factory = RepositoryFactory(RepositorySettings())

    first = factory.create()
    second = factory.create()

    assert first is not second
    assert first.run_repository is not second.run_repository
    assert first.timeline_repository is not second.timeline_repository
    assert (
        first.quality_gate_result_repository
        is not second.quality_gate_result_repository
    )
    assert first.branding_repository is not second.branding_repository


def test_factory_creates_sqlite_repositories(tmp_path: Path) -> None:
    database = tmp_path / "custom.db"
    repositories = RepositoryFactory(
        RepositorySettings(
            storage_backend=StorageBackend.SQLITE,
            sqlite_database=database,
        )
    ).create()

    assert isinstance(repositories.run_repository, SQLiteRunRepository)
    assert isinstance(
        repositories.timeline_repository,
        SQLiteTimelineRepository,
    )
    assert isinstance(
        repositories.quality_gate_result_repository,
        SQLiteQualityGateResultRepository,
    )
    assert isinstance(repositories.branding_repository, SQLiteBrandingRepository)
    assert database.exists()


@pytest.mark.parametrize("backend", list(StorageBackend))
def test_query_metrics_and_api_work_with_each_backend(
    backend: StorageBackend,
    tmp_path: Path,
) -> None:
    settings = RepositorySettings(
        storage_backend=backend,
        storage_directory=(
            tmp_path / backend.value
            if backend is StorageBackend.FILE
            else None
        ),
        sqlite_database=tmp_path / "asep.db",
    )
    repositories = RepositoryFactory(settings).create()
    repositories.run_repository.save(
        Run(
            id="run",
            status=RunStatus.SUCCEEDED,
            started_at=NOW,
            finished_at=NOW + timedelta(seconds=2),
            provider_name="codex",
        )
    )
    repositories.timeline_repository.append(
        TimelineEvent(
            id="event",
            run_id="run",
            timestamp=NOW,
            type=TimelineEventType.RUN_STARTED,
        )
    )
    query = RunQueryService(
        repositories.run_repository,
        repositories.timeline_repository,
    )
    metrics = MetricsService(query)
    client = TestClient(create_app(query, metrics))

    assert query.get_run("run").status is RunStatus.SUCCEEDED
    assert query.get_timeline("run")[0].id == "event"
    assert metrics.get_summary().success_rate == 1
    assert client.get("/api/v1/runs").json()["items"][0]["id"] == "run"
    assert (
        client.get("/api/v1/runs/run/timeline").json()["items"][0]["id"]
        == "event"
    )
    assert (
        client.get("/api/v1/metrics/summary").json()["success_rate"]
        == 1
    )


def test_default_api_composition_accepts_file_settings(
    tmp_path: Path,
) -> None:
    settings = RepositorySettings(
        storage_backend=StorageBackend.FILE,
        storage_directory=tmp_path,
    )

    app = create_default_app(settings)

    assert TestClient(app).get("/api/v1/runs").json() == {"items": []}
    assert (tmp_path / "runs.json").exists()


def test_concrete_creation_is_centralized_in_factory() -> None:
    package_root = Path(asep.__file__).parent
    creation_patterns = (
        "InMemoryRunRepository()",
        "FileRunRepository(",
        "InMemoryTimelineRepository()",
        "FileTimelineRepository(",
        "SQLiteRunRepository(",
        "SQLiteTimelineRepository(",
    )
    violations: list[str] = []
    for path in package_root.rglob("*.py"):
        relative = path.relative_to(package_root).as_posix()
        if relative in {
            "repositories/factory.py",
            "runs/file_repository.py",
            "timeline/file_repository.py",
            "runs/sqlite_repository.py",
            "timeline/sqlite_repository.py",
        }:
            continue
        source = path.read_text(encoding="utf-8")
        for pattern in creation_patterns:
            if pattern in source:
                violations.append(f"{relative}: {pattern}")

    assert violations == []


def test_services_depend_on_protocols_not_concrete_repositories() -> None:
    import asep.application.run_query as query
    import asep.metrics.service as metrics

    source = inspect.getsource(query) + inspect.getsource(metrics)
    for concrete in (
        "InMemoryRunRepository",
        "FileRunRepository",
        "InMemoryTimelineRepository",
        "FileTimelineRepository",
        "SQLiteRunRepository",
        "SQLiteTimelineRepository",
    ):
        assert concrete not in source


def test_public_exports_are_intentional() -> None:
    import asep.repositories as repositories

    assert set(repositories.__all__) == {
        "RepositoryBundle",
        "RepositoryConfigurationError",
        "RepositoryFactory",
        "RepositorySettings",
        "StorageBackend",
    }
