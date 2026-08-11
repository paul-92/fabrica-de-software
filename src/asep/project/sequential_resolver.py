"""Explicit allow-list resolver for filesystem sequential projects."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from types import MappingProxyType

from pydantic import ValidationError

from asep.application.sequential_projects import (
    AuthorizedSequentialProject,
    SequentialProjectIdentityMismatchError,
    SequentialProjectNotFoundError,
    SequentialProjectPathError,
)
from asep.errors import ConfigurationError
from asep.models import ProjectDefinition
from asep.yaml_io import load_yaml


class ConfiguredSequentialProjectResolver:
    """Resolve only projects explicitly registered by the composition host."""

    def __init__(
        self,
        registrations: Iterable[AuthorizedSequentialProject] = (),
        *,
        authorized_roots: Iterable[Path] = (),
    ) -> None:
        roots = tuple(Path(root).expanduser().resolve() for root in authorized_roots)
        projects: dict[str, AuthorizedSequentialProject] = {}
        for registration in registrations:
            project_id = registration.project_id.strip()
            if not project_id:
                raise SequentialProjectIdentityMismatchError(
                    "Identificador de projeto sequencial nao pode ser vazio."
                )
            if project_id in projects:
                raise SequentialProjectIdentityMismatchError(
                    f"Projeto sequencial registrado mais de uma vez: {project_id}"
                )
            project_path = Path(registration.project_path).expanduser().resolve()
            if roots and not any(
                project_path == root or root in project_path.parents for root in roots
            ):
                raise SequentialProjectPathError(
                    f"Caminho nao autorizado para o projeto sequencial: {project_id}"
                )
            if not project_path.is_dir():
                raise SequentialProjectPathError(
                    f"Diretorio indisponivel para o projeto sequencial: {project_id}"
                )
            try:
                definition = ProjectDefinition.model_validate(
                    load_yaml(project_path / "project.yaml")
                )
            except (
                ConfigurationError,
                OSError,
                UnicodeError,
                ValidationError,
            ) as exc:
                raise SequentialProjectPathError(
                    "Manifesto indisponivel ou invalido para o projeto "
                    f"sequencial: {project_id}"
                ) from exc
            if definition.id != project_id:
                raise SequentialProjectIdentityMismatchError(
                    "Identidade declarativa divergente para o projeto "
                    f"sequencial: {project_id}"
                )
            projects[project_id] = AuthorizedSequentialProject(project_id, project_path)
        self._projects = MappingProxyType(projects)

    def resolve(self, project_id: str) -> AuthorizedSequentialProject:
        normalized_id = project_id.strip()
        if not normalized_id:
            raise SequentialProjectNotFoundError("Projeto sequencial nao encontrado.")
        try:
            return self._projects[normalized_id]
        except KeyError as exc:
            raise SequentialProjectNotFoundError(
                f"Projeto sequencial nao encontrado: {normalized_id}"
            ) from exc


__all__ = ["ConfiguredSequentialProjectResolver"]
