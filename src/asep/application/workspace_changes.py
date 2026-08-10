"""Snapshots confinados para evidência de mudanças no workspace."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from asep.workspace_changes import WorkspaceChange, WorkspaceChangeType


class WorkspaceSnapshotPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_files: int = Field(default=10_000, ge=1)
    max_file_size: int = Field(default=10 * 1024 * 1024, ge=1)
    max_total_bytes: int = Field(default=100 * 1024 * 1024, ge=1)


class WorkspaceSnapshotLimitError(Exception):
    pass


class _FileState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    digest: str
    size: int


WorkspaceSnapshot = dict[str, _FileState]

_BLOCKED_NAMES = {".env", ".netrc", "credentials", "credentials.json"}
_BLOCKED_DIRS = {".git", ".ssh"}


class WorkspaceSnapshotter:
    def __init__(self, policy: WorkspaceSnapshotPolicy | None = None) -> None:
        self.policy = policy or WorkspaceSnapshotPolicy()

    def capture(self, workspace: Path) -> WorkspaceSnapshot:
        root = workspace.expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError("workspace deve existir e ser diretório")
        snapshot: WorkspaceSnapshot = {}
        total = 0
        pending = [root]
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    if self._blocked(entry.name) or self._reparse(entry):
                        continue
                    path = Path(entry.path)
                    try:
                        path.resolve().relative_to(root)
                    except (OSError, ValueError):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(path)
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    info = entry.stat(follow_symlinks=False)
                    if info.st_size > self.policy.max_file_size:
                        raise WorkspaceSnapshotLimitError(
                            "arquivo excede limite do snapshot"
                        )
                    total += info.st_size
                    if (
                        len(snapshot) >= self.policy.max_files
                        or total > self.policy.max_total_bytes
                    ):
                        raise WorkspaceSnapshotLimitError(
                            "workspace excede limites do snapshot"
                        )
                    relative = path.relative_to(root).as_posix()
                    snapshot[relative] = _FileState(
                        digest=self._digest(path), size=info.st_size
                    )
        return snapshot

    @staticmethod
    def changes(
        before: WorkspaceSnapshot, after: WorkspaceSnapshot
    ) -> tuple[WorkspaceChange, ...]:
        changes: list[WorkspaceChange] = []
        for path in sorted(set(before) | set(after)):
            old, new = before.get(path), after.get(path)
            if old is None and new is not None:
                changes.append(WorkspaceChange(
                    path=path, change_type=WorkspaceChangeType.CREATED,
                    size_after=new.size,
                ))
            elif old is not None and new is None:
                changes.append(WorkspaceChange(
                    path=path, change_type=WorkspaceChangeType.DELETED,
                    size_before=old.size,
                ))
            elif old is not None and new is not None and old.digest != new.digest:
                changes.append(WorkspaceChange(
                    path=path, change_type=WorkspaceChangeType.MODIFIED,
                    size_before=old.size, size_after=new.size,
                ))
        return tuple(changes)

    @staticmethod
    def _blocked(name: str) -> bool:
        normalized = name.casefold()
        return (
            normalized in _BLOCKED_DIRS
            or normalized in _BLOCKED_NAMES
            or normalized.startswith(".env.")
        )

    @staticmethod
    def _reparse(entry: os.DirEntry[str]) -> bool:
        if entry.is_symlink():
            return True
        attributes = getattr(
            entry.stat(follow_symlinks=False), "st_file_attributes", 0
        )
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))

    @staticmethod
    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


__all__ = [
    "WorkspaceChange",
    "WorkspaceChangeType",
    "WorkspaceSnapshotLimitError",
    "WorkspaceSnapshotPolicy",
    "WorkspaceSnapshotter",
]
