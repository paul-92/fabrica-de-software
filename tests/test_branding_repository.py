from __future__ import annotations

import inspect
import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

import asep.branding as branding
from asep.branding import (
    BRANDING_STORAGE_VERSION,
    DEFAULT_BRANDING_SETTINGS,
    BrandingRepository,
    BrandingSettings,
    FileBrandingRepository,
    InMemoryBrandingRepository,
    InvalidBrandingStorageFormatError,
    SQLiteBrandingRepository,
    UnsupportedBrandingStorageVersionError,
)
from asep.configuration import ApplicationSettings, StorageBackend
from asep.repositories import RepositoryFactory


def settings(**updates: object) -> BrandingSettings:
    values = DEFAULT_BRANDING_SETTINGS.model_dump()
    values.update(updates)
    return BrandingSettings.model_validate(values)


def repositories(tmp_path: Path) -> tuple[BrandingRepository, ...]:
    return (
        InMemoryBrandingRepository(),
        FileBrandingRepository(tmp_path / "branding.json"),
        SQLiteBrandingRepository(tmp_path / "branding.db"),
    )


def test_canonical_defaults_are_valid_and_exact() -> None:
    assert DEFAULT_BRANDING_SETTINGS == BrandingSettings(
        product_name="Engineering Platform",
        short_name="EP",
        logo_url=None,
        workspace_label="Área de trabalho",
        footer_text="Engenharia com segurança",
    )


def test_model_is_frozen_strict_and_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        DEFAULT_BRANDING_SETTINGS.product_name = "Changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        BrandingSettings.model_validate(
            {**DEFAULT_BRANDING_SETTINGS.model_dump(), "unknown": "value"}
        )
    with pytest.raises(ValidationError):
        settings(product_name=123)


@pytest.mark.parametrize(
    ("field", "maximum"),
    [
        ("product_name", 120),
        ("short_name", 12),
        ("workspace_label", 80),
        ("footer_text", 200),
    ],
)
def test_text_fields_trim_validate_boundaries_and_reject_controls(
    field: str, maximum: int
) -> None:
    assert getattr(settings(**{field: "  Valid  "}), field) == "Valid"
    assert len(getattr(settings(**{field: "x" * maximum}), field)) == maximum
    for invalid in (
        "",
        "   ",
        "x" * (maximum + 1),
        "bad\nvalue",
        "bad\x00value",
        "\tbad",
        "bad\r",
    ):
        with pytest.raises(ValidationError):
            settings(**{field: invalid})


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/logo.png",
        "/logo.png",
        "logo.png",
        "data:image/png;base64,AAAA",
        "file:///tmp/logo.png",
        "javascript:alert(1)",
        "https://user@example.com/logo.png",
        "https://user:password@example.com/logo.png",
        "https://example.com/logo.png#fragment",
        "https://example.com/logo.png#",
        "\thttps://example.com/logo.png",
        "https:///logo.png",
        "https://example.com/" + "x" * 2040,
    ],
)
def test_logo_url_rejects_unsafe_or_non_absolute_values(url: str) -> None:
    with pytest.raises(ValidationError):
        settings(logo_url=url)


def test_logo_url_accepts_trimmed_absolute_https_url() -> None:
    configured = settings(logo_url="  https://cdn.example.com/logo.png?v=1  ")
    assert configured.logo_url == "https://cdn.example.com/logo.png?v=1"


@pytest.mark.parametrize("index", range(3))
def test_repository_parity_empty_replace_detached_and_replacement(
    tmp_path: Path, index: int
) -> None:
    repository = repositories(tmp_path)[index]
    assert isinstance(repository, BrandingRepository)
    assert repository.get() is None

    first = settings(product_name="First")
    repository.replace(first)
    restored = repository.get()
    assert restored == first
    assert restored is not first

    second = settings(product_name="Second", logo_url="https://example.com/logo.svg")
    repository.replace(second)
    restored_again = repository.get()
    assert restored_again == second
    assert restored_again is not second
    assert restored_again is not restored


def test_independent_in_memory_repositories_are_isolated() -> None:
    first = InMemoryBrandingRepository()
    second = InMemoryBrandingRepository()
    first.replace(settings(product_name="First"))
    assert second.get() is None


def test_file_absence_does_not_create_override(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "branding.json"
    assert FileBrandingRepository(path).get() is None
    assert not path.exists()


def test_file_format_reconstruction_replace_and_isolation(tmp_path: Path) -> None:
    first_path = tmp_path / "first" / "branding.json"
    second_path = tmp_path / "second" / "branding.json"
    expected = settings(product_name="Persisted")
    repository = FileBrandingRepository(first_path)
    repository.replace(expected)

    document = json.loads(first_path.read_text(encoding="utf-8"))
    assert document == {
        "version": BRANDING_STORAGE_VERSION,
        "branding": expected.model_dump(mode="json"),
    }
    assert FileBrandingRepository(first_path).get() == expected
    assert FileBrandingRepository(second_path).get() is None

    replacement = settings(product_name="Replacement")
    FileBrandingRepository(first_path).replace(replacement)
    assert FileBrandingRepository(first_path).get() == replacement


@pytest.mark.parametrize(
    ("document", "error"),
    [
        ({"version": "2.0", "branding": {}}, UnsupportedBrandingStorageVersionError),
        ({"version": "1.0", "branding": {}}, InvalidBrandingStorageFormatError),
        ({"version": "1.0", "branding": {**DEFAULT_BRANDING_SETTINGS.model_dump(), "extra": 1}}, InvalidBrandingStorageFormatError),
        ({"version": "1.0", "branding": []}, InvalidBrandingStorageFormatError),
        ({"version": "1.0", "branding": DEFAULT_BRANDING_SETTINGS.model_dump(), "extra": 1}, InvalidBrandingStorageFormatError),
    ],
)
def test_file_rejects_invalid_envelopes(
    tmp_path: Path, document: object, error: type[Exception]
) -> None:
    path = tmp_path / "branding.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(error):
        FileBrandingRepository(path)


@pytest.mark.parametrize("content", ["{", "", "NaN"])
def test_file_rejects_malformed_json(tmp_path: Path, content: str) -> None:
    path = tmp_path / "branding.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(InvalidBrandingStorageFormatError):
        FileBrandingRepository(path)


def test_file_uses_atomic_replacement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import asep.branding.file_repository as module

    calls: list[tuple[Path, Path]] = []
    real_replace = module.os.replace

    def observed_replace(source: Path, target: Path) -> None:
        calls.append((Path(source), Path(target)))
        real_replace(source, target)

    monkeypatch.setattr(module.os, "replace", observed_replace)
    path = tmp_path / "branding.json"
    FileBrandingRepository(path).replace(settings())
    assert len(calls) == 1
    assert calls[0][0] != path
    assert calls[0][0].parent == path.parent
    assert calls[0][1] == path


def test_sqlite_reconstructs_replaces_singleton_and_preserves_existing_database(
    tmp_path: Path,
) -> None:
    path = tmp_path / "existing.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE existing_data (value TEXT NOT NULL)")
        connection.execute("INSERT INTO existing_data VALUES ('preserved')")

    repository = SQLiteBrandingRepository(path)
    assert repository.get() is None
    repository.replace(settings(product_name="First"))
    repository.replace(settings(product_name="Last"))
    assert SQLiteBrandingRepository(path).get() == settings(product_name="Last")

    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM branding_settings").fetchone()[0] == 1
        assert connection.execute("SELECT value FROM existing_data").fetchone()[0] == "preserved"


@pytest.mark.parametrize(
    ("version", "payload", "error"),
    [
        ("1.0", "{", InvalidBrandingStorageFormatError),
        ("1.0", "{}", InvalidBrandingStorageFormatError),
        ("2.0", json.dumps(DEFAULT_BRANDING_SETTINGS.model_dump()), UnsupportedBrandingStorageVersionError),
    ],
)
def test_sqlite_rejects_malformed_persisted_payload(
    tmp_path: Path, version: str, payload: str, error: type[Exception]
) -> None:
    path = tmp_path / "branding.db"
    SQLiteBrandingRepository(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO branding_settings (id, version, payload) VALUES (?, ?, ?)",
            ("runtime", version, payload),
        )
    with pytest.raises(error):
        SQLiteBrandingRepository(path).get()


@pytest.mark.parametrize(
    ("backend", "implementation"),
    [
        (StorageBackend.MEMORY, InMemoryBrandingRepository),
        (StorageBackend.FILE, FileBrandingRepository),
        (StorageBackend.SQLITE, SQLiteBrandingRepository),
    ],
)
def test_factory_selects_one_branding_repository_per_bundle(
    tmp_path: Path,
    backend: StorageBackend,
    implementation: type[BrandingRepository],
) -> None:
    bundle = RepositoryFactory(ApplicationSettings(
        storage_backend=backend,
        storage_directory=tmp_path / "storage",
        sqlite_database=tmp_path / "asep.db",
    )).create()
    assert isinstance(bundle.branding_repository, implementation)
    assert isinstance(bundle.branding_repository, BrandingRepository)
    assert bundle.run_repository is not None
    assert bundle.session_memory_repository is not None
    assert bundle.quality_gate_result_repository is not None


def test_factory_memory_compositions_have_isolated_branding_ownership() -> None:
    factory = RepositoryFactory(ApplicationSettings())
    first = factory.create()
    second = factory.create()
    assert first.branding_repository is not second.branding_repository
    first.branding_repository.replace(settings(product_name="First"))
    assert second.branding_repository.get() is None


def test_factory_file_and_sqlite_reconstruct_from_explicit_shared_storage(
    tmp_path: Path,
) -> None:
    for configuration in (
        ApplicationSettings(storage_backend="file", storage_directory=tmp_path / "file"),
        ApplicationSettings(storage_backend="sqlite", sqlite_database=tmp_path / "asep.db"),
    ):
        first = RepositoryFactory(configuration).create()
        first.branding_repository.replace(settings(product_name="Shared storage"))
        second = RepositoryFactory(configuration).create()
        assert second.branding_repository is not first.branding_repository
        assert second.branding_repository.get() == settings(product_name="Shared storage")


def test_branding_architecture_has_no_transport_or_frontend_dependencies() -> None:
    package = Path(branding.__file__).parent
    source = "\n".join(path.read_text(encoding="utf-8") for path in package.glob("*.py"))
    assert "fastapi" not in source.lower()
    assert "react" not in source.lower()
    assert "frontend" not in source.lower()

    repository_source = inspect.getsource(__import__("asep.branding.repository", fromlist=["*"]))
    for concrete in ("InMemoryBrandingRepository", "FileBrandingRepository", "SQLiteBrandingRepository"):
        assert concrete not in repository_source


def test_http_layer_does_not_create_or_import_branding_persistence() -> None:
    api_root = Path(__import__("asep.api", fromlist=["*"]).__file__).parent
    source = "\n".join(path.read_text(encoding="utf-8") for path in api_root.glob("*.py"))
    assert "BrandingRepository" not in source
    assert "BrandingRepository(" not in source
    assert "/api/v1/branding" not in source
