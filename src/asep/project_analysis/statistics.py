"""Cálculo das estatísticas agregadas do projeto."""

from __future__ import annotations

from asep.project_analysis.models import (
    Dependency,
    Entrypoint,
    LanguageStatistics,
    ProjectModule,
    ProjectStatistics,
    ScannedProject,
)

_DOC_NAMES = {"readme", "changelog", "contributing", "license"}


class StatisticsCalculator:
    def calculate(
        self,
        scanned: ScannedProject,
        languages: tuple[LanguageStatistics, ...],
        modules: tuple[ProjectModule, ...],
        entrypoints: tuple[Entrypoint, ...],
        dependencies: tuple[Dependency, ...],
    ) -> ProjectStatistics:
        tests = sum(
            item.path.name.startswith("test_")
            or item.path.name.endswith((".test.js", ".test.ts", ".spec.ts"))
            or "tests" in {part.lower() for part in item.path.parts}
            for item in scanned.files
        )
        docs = sum(
            item.path.suffix.lower() in {".md", ".rst"}
            or item.path.stem.lower() in _DOC_NAMES
            for item in scanned.files
        )
        lines = {item.name: item.line_count for item in languages}
        return ProjectStatistics(
            file_count=len(scanned.files),
            directory_count=len(scanned.directories),
            lines_of_code=sum(lines.values()),
            lines_by_language=dict(sorted(lines.items())),
            test_file_count=tests,
            documentation_file_count=docs,
            maximum_depth=scanned.maximum_depth,
            module_count=len(modules),
            entrypoint_count=len(entrypoints),
            dependency_count=len(dependencies),
        )


__all__ = ["StatisticsCalculator"]
