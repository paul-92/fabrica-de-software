"""Heurísticas determinísticas para frameworks suportados."""

from __future__ import annotations

from asep.project_analysis.models import (
    Dependency,
    FrameworkDetection,
    ScannedProject,
)

_FRAMEWORKS = {
    "fastapi": ("FastAPI", "Python"),
    "flask": ("Flask", "Python"),
    "django": ("Django", "Python"),
    "streamlit": ("Streamlit", "Python"),
    "react": ("React", "JavaScript"),
    "next": ("Next.js", "JavaScript"),
    "vue": ("Vue", "JavaScript"),
    "@angular/core": ("Angular", "JavaScript"),
    "express": ("Express", "JavaScript"),
}


class FrameworkDetector:
    def detect(
        self,
        scanned: ScannedProject,
        dependencies: tuple[Dependency, ...],
    ) -> tuple[FrameworkDetection, ...]:
        evidence: dict[str, set[str]] = {}
        dependency_names = {item.name.lower() for item in dependencies}
        for key, (name, _) in _FRAMEWORKS.items():
            if key in dependency_names:
                evidence.setdefault(name, set()).add(f"dependency:{key}")
        names = {item.path.name.lower() for item in scanned.files}
        if "manage.py" in names:
            evidence.setdefault("Django", set()).add("file:manage.py")
        if "next.config.js" in names or "next.config.mjs" in names:
            evidence.setdefault("Next.js", set()).add("file:next.config")
        for item in scanned.files:
            if item.path.suffix.lower() not in {
                ".py",
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
            }:
                continue
            try:
                content = (scanned.root_path / item.path).read_text(
                    encoding="utf-8", errors="ignore"
                ).lower()
            except OSError:
                continue
            for key, (name, _) in _FRAMEWORKS.items():
                markers = (
                    f"import {key}",
                    f"from {key}",
                    f"require('{key}')",
                    f'require("{key}")',
                    f"from '{key}'",
                    f'from "{key}"',
                )
                if any(marker in content for marker in markers):
                    evidence.setdefault(name, set()).add(
                        f"import:{item.path.as_posix()}"
                    )
        ecosystems = {
            name: ecosystem for _, (name, ecosystem) in _FRAMEWORKS.items()
        }
        return tuple(
            FrameworkDetection(
                name=name,
                ecosystem=ecosystems[name],
                evidence=tuple(sorted(items)),
            )
            for name, items in sorted(evidence.items())
        )


__all__ = ["FrameworkDetector"]
