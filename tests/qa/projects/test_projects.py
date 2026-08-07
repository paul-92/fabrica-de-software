from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.application import ProjectService
from asep.errors import ProjectNotFoundError, ProjectValidationError
from asep.projects import InMemoryProjectRepository, SQLiteProjectRepository


NOW = datetime(2026, 8, 7, tzinfo=UTC)


def service(repository=None) -> ProjectService:
    return ProjectService(
        repository or InMemoryProjectRepository(),
        clock=lambda: NOW,
        id_generator=lambda: "project-1",
    )


def test_create_list_and_get_project(tmp_path: Path) -> None:
    projects = service()
    created = projects.create(" Sample ", tmp_path)
    assert created.name == "Sample"
    assert created.workspace_path == tmp_path.resolve()
    assert projects.list() == (created,)
    assert projects.get("project-1") == created


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_is_rejected(name: str, tmp_path: Path) -> None:
    with pytest.raises(ProjectValidationError):
        service().create(name, tmp_path)


def test_missing_or_file_workspace_is_rejected(tmp_path: Path) -> None:
    file = tmp_path / "file.txt"
    file.write_text("x", encoding="utf-8")
    for path in (tmp_path / "missing", file):
        with pytest.raises(ProjectValidationError):
            service().create("Project", path)


def test_not_found_is_explicit() -> None:
    with pytest.raises(ProjectNotFoundError):
        service().get("missing")


def test_sqlite_repository_persists_between_instances(tmp_path: Path) -> None:
    database = tmp_path / "asep.db"
    created = service(SQLiteProjectRepository(database)).create("Project", tmp_path)
    assert SQLiteProjectRepository(database).get(created.project_id) == created
