"""Extração determinística de dependências declaradas."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

from asep.project_analysis.models import Dependency, ScannedProject

_REQUIREMENT = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)\s*(.*?)(?:\s*;\s*.*)?$"
)


class DependencyAnalyzer:
    def analyze(self, scanned: ScannedProject) -> tuple[Dependency, ...]:
        paths = {item.path for item in scanned.files}
        dependencies: list[Dependency] = []
        if Path("pyproject.toml") in paths:
            dependencies.extend(
                self._pyproject(scanned.root_path / "pyproject.toml")
            )
        if Path("requirements.txt") in paths:
            dependencies.extend(
                self._requirements(
                    scanned.root_path / "requirements.txt",
                    Path("requirements.txt"),
                )
            )
        if Path("package.json") in paths:
            dependencies.extend(
                self._package_json(scanned.root_path / "package.json")
            )
        unique = {
            (item.name.lower(), item.source, item.scope): item
            for item in dependencies
        }
        return tuple(
            sorted(
                unique.values(),
                key=lambda item: (
                    item.source.as_posix(),
                    item.scope,
                    item.name.lower(),
                ),
            )
        )

    def _pyproject(self, path: Path) -> list[Dependency]:
        document = self._read_toml(path)
        result = self._requirement_list(
            document.get("project", {}).get("dependencies", ()),
            Path("pyproject.toml"),
        )
        optional = document.get("project", {}).get(
            "optional-dependencies", {}
        )
        if isinstance(optional, dict):
            for scope, values in optional.items():
                result.extend(
                    self._requirement_list(
                        values, Path("pyproject.toml"), str(scope)
                    )
                )
        poetry = (
            document.get("tool", {})
            .get("poetry", {})
            .get("dependencies", {})
        )
        if isinstance(poetry, dict):
            for name, version in poetry.items():
                if str(name).lower() == "python":
                    continue
                result.append(
                    Dependency(
                        name=str(name),
                        version=self._version_text(version),
                        source=Path("pyproject.toml"),
                    )
                )
        return result

    def _requirements(
        self, path: Path, source: Path
    ) -> list[Dependency]:
        try:
            lines = path.read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines()
        except OSError:
            return []
        return self._requirement_list(
            (
                line
                for line in lines
                if line.strip()
                and not line.lstrip().startswith(("#", "-", "http:"))
                and not line.lstrip().startswith("https:")
            ),
            source,
        )

    def _package_json(self, path: Path) -> list[Dependency]:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []
        if not isinstance(document, dict):
            return []
        result: list[Dependency] = []
        for field, scope in (
            ("dependencies", "runtime"),
            ("devDependencies", "development"),
            ("peerDependencies", "peer"),
        ):
            values = document.get(field, {})
            if not isinstance(values, dict):
                continue
            result.extend(
                Dependency(
                    name=str(name),
                    version=str(version),
                    source=Path("package.json"),
                    scope=scope,
                )
                for name, version in values.items()
            )
        return result

    @staticmethod
    def _read_toml(path: Path) -> dict[str, Any]:
        try:
            with path.open("rb") as stream:
                document = tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError):
            return {}
        return document

    @staticmethod
    def _version_text(value: Any) -> str:
        if isinstance(value, dict):
            version = value.get("version")
            return "" if version is None else str(version)
        return str(value)

    @staticmethod
    def _requirement_list(
        values, source: Path, scope: str = "runtime"
    ) -> list[Dependency]:
        result = []
        if isinstance(values, (str, bytes)) or not hasattr(
            values, "__iter__"
        ):
            return result
        for raw in values:
            match = _REQUIREMENT.match(str(raw))
            if match is None:
                continue
            version = match.group(2).strip() or None
            result.append(
                Dependency(
                    name=match.group(1),
                    version=version,
                    source=source,
                    scope=scope,
                )
            )
        return result


__all__ = ["DependencyAnalyzer"]
