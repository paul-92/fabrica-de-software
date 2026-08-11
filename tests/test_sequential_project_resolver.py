from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from asep.application import (
    AuthorizedSequentialProject,
    SequentialProjectIdentityMismatchError,
    SequentialProjectNotFoundError,
    SequentialProjectPathError,
    SequentialProjectResolver,
)
from asep.orchestrator import create_sequential_operational_composition
from asep.project.sequential_resolver import ConfiguredSequentialProjectResolver


def project(root: Path, project_id: str = "sample") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "project.yaml").write_text(
        "\n".join((
            f"id: {project_id}", "name: Test", "version: 0.1.0",
            "status: active", "project_type: software",
            "workflow_id: software-project", "data_classification: internal",
        )),
        encoding="utf-8",
    )
    return root


def registration(project_id: str, path: Path) -> AuthorizedSequentialProject:
    return AuthorizedSequentialProject(project_id, path)


def test_resolver_is_typed_deterministic_and_returns_frozen_context(
    tmp_path: Path,
) -> None:
    path = project(tmp_path / "projects" / "sample")
    resolver = ConfiguredSequentialProjectResolver(
        (registration("sample", path),), authorized_roots=(tmp_path / "projects",)
    )

    first = resolver.resolve("sample")
    assert isinstance(resolver, SequentialProjectResolver)
    assert first is resolver.resolve("sample")
    assert first.project_path == path.resolve()
    with pytest.raises(FrozenInstanceError):
        first.project_id = "other"  # type: ignore[misc]


def test_unknown_project_is_typed_and_does_not_leak_paths(tmp_path: Path) -> None:
    resolver = ConfiguredSequentialProjectResolver()
    with pytest.raises(SequentialProjectNotFoundError) as caught:
        resolver.resolve("unknown")
    assert str(tmp_path.resolve()) not in str(caught.value)


def test_duplicate_project_ids_are_rejected(tmp_path: Path) -> None:
    path = project(tmp_path / "sample")
    with pytest.raises(SequentialProjectIdentityMismatchError):
        ConfiguredSequentialProjectResolver((
            registration("sample", path), registration("sample", path),
        ))


def test_declarative_identity_mismatch_is_rejected(tmp_path: Path) -> None:
    path = project(tmp_path / "sample", "declared")
    with pytest.raises(SequentialProjectIdentityMismatchError):
        ConfiguredSequentialProjectResolver((registration("requested", path),))


def test_missing_and_unreadable_manifest_errors_do_not_leak_path(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(SequentialProjectPathError) as missing_error:
        ConfiguredSequentialProjectResolver((registration("sample", missing),))
    assert str(missing.resolve()) not in str(missing_error.value)

    invalid = tmp_path / "invalid"
    invalid.mkdir()
    (invalid / "project.yaml").write_text("id: [", encoding="utf-8")
    with pytest.raises(SequentialProjectPathError) as invalid_error:
        ConfiguredSequentialProjectResolver((registration("sample", invalid),))
    assert str(invalid.resolve()) not in str(invalid_error.value)


def test_path_outside_authorized_root_is_rejected_without_path_leak(
    tmp_path: Path,
) -> None:
    outside = project(tmp_path / "outside")
    with pytest.raises(SequentialProjectPathError) as caught:
        ConfiguredSequentialProjectResolver(
            (registration("sample", outside),),
            authorized_roots=(tmp_path / "authorized",),
        )
    assert str(outside.resolve()) not in str(caught.value)


def test_composition_uses_exact_injected_resolver_and_isolates_instances(
    tmp_path: Path,
) -> None:
    path = project(tmp_path / "sample")
    resolver = ConfiguredSequentialProjectResolver((registration("sample", path),))
    first = create_sequential_operational_composition(project_resolver=resolver)
    second = create_sequential_operational_composition(
        authorized_projects=(registration("sample", path),)
    )

    assert first.sequential_project_resolver is resolver
    assert second.sequential_project_resolver is not resolver
    assert first.sequential_execution_source is not second.sequential_execution_source
