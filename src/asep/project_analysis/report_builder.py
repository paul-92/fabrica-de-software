"""Montagem final do relatório imutável de análise."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable, Mapping

from pydantic import JsonValue

from asep.project_analysis.models import (
    ArchitectureDetection,
    Dependency,
    Entrypoint,
    FrameworkDetection,
    LanguageStatistics,
    PackageManagerDetection,
    ProjectAnalysis,
    ProjectModule,
    ProjectStatistics,
    ScannedProject,
)

Clock = Callable[[], datetime]


class ProjectAnalysisReportBuilder:
    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def build(
        self,
        *,
        scanned: ScannedProject,
        languages: tuple[LanguageStatistics, ...],
        frameworks: tuple[FrameworkDetection, ...],
        package_managers: tuple[PackageManagerDetection, ...],
        modules: tuple[ProjectModule, ...],
        entrypoints: tuple[Entrypoint, ...],
        architecture: tuple[ArchitectureDetection, ...],
        dependencies: tuple[Dependency, ...],
        statistics: ProjectStatistics,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> ProjectAnalysis:
        return ProjectAnalysis(
            root_path=scanned.root_path,
            project_name=scanned.root_path.name,
            languages=languages,
            frameworks=frameworks,
            package_managers=package_managers,
            modules=modules,
            entrypoints=entrypoints,
            architecture=architecture,
            dependencies=dependencies,
            statistics=statistics,
            metadata={
                "analyzer": "asep.project_analysis",
                "heuristics_version": "1.0",
                **(metadata or {}),
            },
            generated_at=self._clock(),
        )


__all__ = ["ProjectAnalysisReportBuilder"]
