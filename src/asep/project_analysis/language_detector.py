"""Detecção de linguagens por extensões conhecidas."""

from __future__ import annotations

from pathlib import Path

from asep.project_analysis.models import (
    LanguageStatistics,
    ScannedProject,
)

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
}


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as stream:
            return sum(1 for _ in stream)
    except OSError:
        return 0


class LanguageDetector:
    def detect(
        self, scanned: ScannedProject
    ) -> tuple[LanguageStatistics, ...]:
        counts: dict[str, dict[str, object]] = {}
        for item in scanned.files:
            extension = item.path.suffix.lower()
            language = LANGUAGE_EXTENSIONS.get(extension)
            if language is None:
                continue
            entry = counts.setdefault(
                language, {"files": 0, "lines": 0, "extensions": set()}
            )
            entry["files"] = int(entry["files"]) + 1
            entry["lines"] = int(entry["lines"]) + count_lines(
                scanned.root_path / item.path
            )
            extensions = entry["extensions"]
            assert isinstance(extensions, set)
            extensions.add(extension)
        return tuple(
            LanguageStatistics(
                name=name,
                file_count=int(values["files"]),
                line_count=int(values["lines"]),
                extensions=tuple(sorted(values["extensions"])),
            )
            for name, values in sorted(counts.items())
        )


__all__ = ["LANGUAGE_EXTENSIONS", "LanguageDetector", "count_lines"]
