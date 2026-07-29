from pathlib import Path

import pytest

from asep.errors import ProjectNotFoundError, ProjectValidationError
from asep.project.loader import ProjectLoader


def test_project_loader_reads_manifest_readme_and_artifacts(
    sample_repository: Path,
) -> None:
    project_path = sample_repository / "projects/sample"

    project = ProjectLoader().load(project_path)

    assert project.definition.id == "sample"
    assert project.readme.startswith("# Sample")
    assert [path.name for path in project.markdown_artifacts] == ["scope.md", "brief.md"]
    assert ProjectLoader.find_repository_root(project_path) == sample_repository


def test_project_loader_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError, match="não encontrado"):
        ProjectLoader().load(tmp_path / "missing")


def test_project_loader_rejects_unknown_field_without_echoing_value(
    sample_repository: Path,
) -> None:
    path = sample_repository / "projects/sample/project.yaml"
    path.write_text(
        path.read_text(encoding="utf-8") + "secret_field: sensitive-value\n",
        encoding="utf-8",
    )

    with pytest.raises(ProjectValidationError) as error:
        ProjectLoader().load(path.parent)

    assert "extra_forbidden" in str(error.value)
    assert "sensitive-value" not in str(error.value)
