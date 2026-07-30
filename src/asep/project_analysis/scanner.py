"""Scanner determinístico e configurável da árvore de um projeto."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from asep.project_analysis.models import ScannedFile, ScannedProject

DEFAULT_IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".idea",
        ".vscode",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        ".venv",
        "venv",
        "coverage",
        ".pytest_cache",
    }
)


class ProjectScanner:
    def __init__(
        self, ignored_directories: Iterable[str] | None = None
    ) -> None:
        self._ignored = frozenset(
            DEFAULT_IGNORED_DIRECTORIES
            if ignored_directories is None
            else ignored_directories
        )

    def scan(self, project_path: Path) -> ScannedProject:
        root = Path(project_path).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Diretório do projeto não encontrado: {root}")
        files: list[ScannedFile] = []
        directories: list[Path] = []
        maximum_depth = 0
        for current, dirnames, filenames in os.walk(root):
            current_path = Path(current)
            dirnames[:] = sorted(
                name
                for name in dirnames
                if name not in self._ignored and not name.startswith(".")
            )
            relative_dir = current_path.relative_to(root)
            if relative_dir != Path("."):
                directories.append(relative_dir)
                maximum_depth = max(
                    maximum_depth, len(relative_dir.parts)
                )
            for name in sorted(filenames):
                if name.startswith("."):
                    continue
                path = current_path / name
                relative = path.relative_to(root)
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                files.append(ScannedFile(path=relative, size_bytes=size))
                maximum_depth = max(maximum_depth, len(relative.parts))
        return ScannedProject(
            root_path=root,
            files=tuple(files),
            directories=tuple(directories),
            maximum_depth=maximum_depth,
        )


__all__ = ["DEFAULT_IGNORED_DIRECTORIES", "ProjectScanner"]
