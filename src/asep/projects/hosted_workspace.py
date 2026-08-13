from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from asep.errors import ProjectValidationError
from asep.projects.models import WorkspaceProject


@dataclass(frozen=True, slots=True)
class HostedWorkspace:
    workspace_id: str
    path: Path


class HostedWorkspaceManager:
    """Backend-owned mapping between a tenant/project and its workspace."""

    def __init__(self, hosted_root: Path) -> None:
        self.root = hosted_root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._reject_reparse(self.root)

    def provision(self, organization_id: str, project_id: str) -> HostedWorkspace:
        expected = self._expected(organization_id, project_id)
        expected.mkdir(parents=True, exist_ok=False)
        self._assert_confined(expected)
        return HostedWorkspace(workspace_id=str(uuid4()), path=expected)

    def resolve(self, project: WorkspaceProject, expected_workspace_id: str | None = None) -> Path:
        if project.workspace_kind != "hosted":
            return project.workspace_path.expanduser().resolve()
        if expected_workspace_id is not None and expected_workspace_id != project.workspace_id:
            raise ProjectValidationError("Workspace não encontrado.")
        expected = self._expected(project.organization_id, project.project_id)
        stored = project.workspace_path.expanduser().resolve()
        if stored != expected:
            raise ProjectValidationError("Workspace hospedado inválido.")
        self._assert_confined(expected)
        if not expected.is_dir():
            raise ProjectValidationError("Workspace hospedado indisponível.")
        return expected

    def _expected(self, organization_id: str, project_id: str) -> Path:
        for value in (organization_id, project_id):
            if not value or value in {".", ".."} or Path(value).name != value or "/" in value or "\\" in value:
                raise ProjectValidationError("Identidade de workspace inválida.")
        path = (self.root / organization_id / project_id / "workspace").resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ProjectValidationError("Workspace fora do hosted root.") from exc
        return path

    def _assert_confined(self, path: Path) -> None:
        try:
            path.resolve(strict=True).relative_to(self.root)
        except (OSError, ValueError) as exc:
            raise ProjectValidationError("Workspace fora do hosted root.") from exc
        current = self.root
        self._reject_reparse(current)
        for part in path.relative_to(self.root).parts:
            current /= part
            self._reject_reparse(current)

    @staticmethod
    def _reject_reparse(path: Path) -> None:
        try:
            info = path.stat(follow_symlinks=False)
        except OSError as exc:
            raise ProjectValidationError("Workspace hospedado indisponível.") from exc
        if path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
            raise ProjectValidationError("Symlink/reparse point não permitido no workspace hospedado.")

