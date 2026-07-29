"""Project Loader da Sprint 1."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from asep.errors import (
    ConfigurationError,
    ProjectNotFoundError,
    ProjectValidationError,
    describe_validation_error,
)
from asep.models import LoadedProject, ProjectDefinition
from asep.yaml_io import load_yaml


class ProjectLoader:
    """Localiza um projeto e carrega manifesto, README, estado e artefatos."""

    def load(self, project_path: Path) -> LoadedProject:
        path = project_path.expanduser().resolve()
        if not path.is_dir():
            raise ProjectNotFoundError("Diretório do projeto não encontrado.", path=path)
        manifest = path / "project.yaml"
        readme = path / "README.md"
        if not readme.is_file():
            raise ProjectValidationError("README do projeto não encontrado.", path=readme)
        try:
            definition = ProjectDefinition.model_validate(load_yaml(manifest))
        except ValidationError as exc:
            raise ProjectValidationError(
                f"Projeto inválido: {describe_validation_error(exc)}", path=manifest
            ) from exc
        except ConfigurationError as exc:
            raise ProjectValidationError(
                f"Projeto inválido: {exc.message}", path=manifest
            ) from exc
        artifacts = tuple(
            sorted(
                candidate
                for candidate in path.rglob("*.md")
                if candidate.name != "README.md"
            )
        )
        try:
            readme_content = readme.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ProjectValidationError(
                f"README não pôde ser lido: {exc}", path=readme
            ) from exc
        return LoadedProject(
            definition=definition,
            path=path,
            readme=readme_content,
            markdown_artifacts=artifacts,
        )

    @staticmethod
    def find_repository_root(project_path: Path) -> Path:
        """Sobe na árvore até encontrar Registry e workflows."""
        resolved = project_path.expanduser().resolve()
        for candidate in (resolved, *resolved.parents):
            if (candidate / "registry").is_dir() and (candidate / "workflows").is_dir():
                return candidate
        raise ProjectValidationError(
            "Raiz ASEP não encontrada; esperado registry/ e workflows/ nos ancestrais.",
            path=resolved,
        )
