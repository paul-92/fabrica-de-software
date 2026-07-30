"""Detecção determinística de entrypoints por nomes convencionais."""

from __future__ import annotations

from asep.project_analysis.language_detector import LANGUAGE_EXTENSIONS
from asep.project_analysis.models import Entrypoint, ScannedProject

_ENTRYPOINTS = {
    "main.py",
    "__main__.py",
    "index.js",
    "server.js",
    "main.js",
    "app.js",
    "main.ts",
    "server.ts",
    "index.ts",
}


class EntrypointDetector:
    def detect(self, scanned: ScannedProject) -> tuple[Entrypoint, ...]:
        return tuple(
            Entrypoint(
                path=item.path,
                language=LANGUAGE_EXTENSIONS[item.path.suffix.lower()],
            )
            for item in scanned.files
            if item.path.name.lower() in _ENTRYPOINTS
            and item.path.suffix.lower() in LANGUAGE_EXTENSIONS
        )


__all__ = ["EntrypointDetector"]
