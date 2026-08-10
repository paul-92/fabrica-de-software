from __future__ import annotations

import fnmatch
import os
import stat
from pathlib import Path, PureWindowsPath

from pydantic import BaseModel, ConfigDict, Field

from asep.application.projects import ProjectService
from asep.errors import (
    WorkspaceBinaryFileError, WorkspaceDirectoryTooLargeError,
    WorkspaceEntryNotDirectoryError, WorkspaceEntryNotFileError,
    WorkspaceEntryNotFoundError, WorkspaceFileTooLargeError,
    WorkspaceNotFoundError, WorkspacePathForbiddenError,
    WorkspacePathInvalidError,
)
from asep.projects.workspace_models import (
    WorkspaceDirectory, WorkspaceEntry, WorkspaceEntryKind, WorkspaceFileContent,
)


class WorkspaceBrowsingPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_file_size: int = Field(default=1024 * 1024, ge=1)
    max_directory_entries: int = Field(default=1000, ge=1)
    ignored_directory_names: frozenset[str] = frozenset({
        ".git", ".ssh", "__pycache__", "node_modules", ".next",
        ".pytest_cache", "dist", "build",
    })
    sensitive_file_patterns: tuple[str, ...] = (
        ".env", ".env.*", ".netrc", "id_rsa", "id_ed25519",
        "credentials*", "*.pem", "*.key",
    )


class ProjectWorkspaceService:
    def __init__(self, projects: ProjectService, policy: WorkspaceBrowsingPolicy | None = None) -> None:
        self._projects = projects
        self.policy = policy or WorkspaceBrowsingPolicy()

    def list_directory(self, project_id: str, relative_path: str = "") -> WorkspaceDirectory:
        root, target, relative = self._resolve(project_id, relative_path, allow_root=True)
        if not target.is_dir():
            raise WorkspaceEntryNotDirectoryError("Workspace entry is not a directory.")
        entries: list[WorkspaceEntry] = []
        try:
            with os.scandir(target) as discovered:
                for item in discovered:
                    if self._blocked(item.name, item.is_dir(follow_symlinks=False)) or self._reparse(item):
                        continue
                    if len(entries) >= self.policy.max_directory_entries:
                        raise WorkspaceDirectoryTooLargeError("Workspace directory exceeds listing limit.")
                    path = Path(item.path)
                    try:
                        path.resolve(strict=True).relative_to(root)
                        info = item.stat(follow_symlinks=False)
                    except (OSError, ValueError):
                        continue
                    kind = WorkspaceEntryKind.DIRECTORY if item.is_dir(follow_symlinks=False) else WorkspaceEntryKind.FILE
                    if kind is WorkspaceEntryKind.FILE and not item.is_file(follow_symlinks=False):
                        continue
                    entries.append(WorkspaceEntry(
                        path=path.relative_to(root).as_posix(), name=item.name, kind=kind,
                        size=None if kind is WorkspaceEntryKind.DIRECTORY else info.st_size,
                    ))
        except WorkspaceDirectoryTooLargeError:
            raise
        except OSError as exc:
            raise WorkspaceEntryNotFoundError("Workspace directory is unavailable.") from exc
        entries.sort(key=lambda item: (item.kind is WorkspaceEntryKind.FILE, item.name.casefold(), item.name))
        return WorkspaceDirectory(path=relative, entries=tuple(entries))

    def read_file(self, project_id: str, relative_path: str) -> WorkspaceFileContent:
        _root, target, relative = self._resolve(project_id, relative_path, allow_root=False)
        if not target.is_file():
            raise WorkspaceEntryNotFileError("Workspace entry is not a file.")
        size = target.stat().st_size
        if size > self.policy.max_file_size:
            raise WorkspaceFileTooLargeError("Workspace file exceeds preview limit.")
        data = target.read_bytes()
        if len(data) > self.policy.max_file_size:
            raise WorkspaceFileTooLargeError("Workspace file exceeds preview limit.")
        try:
            content = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise WorkspaceBinaryFileError("Binary files cannot be previewed.") from exc
        if "\x00" in content:
            raise WorkspaceBinaryFileError("Binary files cannot be previewed.")
        return WorkspaceFileContent(path=relative, name=target.name, content=content, size=size, language=_language(target.suffix))

    def _resolve(self, project_id: str, value: str, *, allow_root: bool) -> tuple[Path, Path, str]:
        project = self._projects.get(project_id)
        root = project.workspace_path.expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise WorkspaceNotFoundError("Project workspace is unavailable.")
        if not isinstance(value, str) or "\x00" in value:
            raise WorkspacePathInvalidError("Workspace path is invalid.")
        normalized = value.strip().replace("\\", "/")
        if not normalized and not allow_root:
            raise WorkspacePathInvalidError("Workspace file path is required.")
        windows = PureWindowsPath(normalized)
        candidate_input = Path(normalized)
        if candidate_input.is_absolute() or windows.is_absolute() or windows.drive or normalized.startswith("//") or ":" in normalized:
            raise WorkspacePathForbiddenError("Absolute workspace paths are forbidden.")
        if any(part in {"..", "."} for part in candidate_input.parts):
            raise WorkspacePathForbiddenError("Workspace traversal is forbidden.")
        parts = tuple(part for part in candidate_input.parts if part)
        for part in parts:
            if self._blocked(part, True):
                raise WorkspacePathForbiddenError("Sensitive workspace path is forbidden.")
        target = root.joinpath(*parts)
        if not target.exists():
            raise WorkspaceEntryNotFoundError("Workspace entry was not found.")
        current = root
        for part in parts:
            current = current / part
            if self._path_reparse(current):
                raise WorkspacePathForbiddenError("Symlink and reparse paths are forbidden.")
        try:
            target.resolve(strict=True).relative_to(root)
        except (OSError, ValueError) as exc:
            raise WorkspacePathForbiddenError("Workspace path escapes the project.") from exc
        return root, target, "/".join(parts)

    def _blocked(self, name: str, directory: bool) -> bool:
        folded = name.casefold()
        if directory and folded in {item.casefold() for item in self.policy.ignored_directory_names}:
            return True
        return any(fnmatch.fnmatchcase(folded, pattern.casefold()) for pattern in self.policy.sensitive_file_patterns)

    @staticmethod
    def _reparse(entry: os.DirEntry[str]) -> bool:
        if entry.is_symlink(): return True
        return bool(getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))

    @staticmethod
    def _path_reparse(path: Path) -> bool:
        if path.is_symlink(): return True
        try: attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
        except OSError: return True
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _language(suffix: str) -> str:
    return {".py":"python", ".ts":"typescript", ".tsx":"typescriptreact", ".js":"javascript", ".json":"json", ".md":"markdown", ".yml":"yaml", ".yaml":"yaml", ".sql":"sql", ".html":"html", ".css":"css", ".txt":"plaintext"}.get(suffix.casefold(), "plaintext")


__all__ = ["ProjectWorkspaceService", "WorkspaceBrowsingPolicy"]
