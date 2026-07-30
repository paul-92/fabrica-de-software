"""Fachada pública do Project Analyzer."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic import JsonValue

from asep.project_analysis.architecture_detector import ArchitectureDetector
from asep.project_analysis.dependency_analyzer import DependencyAnalyzer
from asep.project_analysis.entrypoint_detector import EntrypointDetector
from asep.project_analysis.framework_detector import FrameworkDetector
from asep.project_analysis.language_detector import LanguageDetector
from asep.project_analysis.models import (
    PackageManagerDetection,
    ProjectAnalysis,
    ProjectModule,
    ScannedProject,
)
from asep.project_analysis.report_builder import ProjectAnalysisReportBuilder
from asep.project_analysis.scanner import ProjectScanner
from asep.project_analysis.statistics import StatisticsCalculator

_PACKAGE_MANAGERS = {
    "pyproject.toml": "pip",
    "requirements.txt": "pip",
    "poetry.lock": "Poetry",
    "pipfile": "Pipenv",
    "package.json": "npm",
    "package-lock.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "Yarn",
}


class ProjectAnalyzer:
    def __init__(
        self,
        *,
        scanner: ProjectScanner | None = None,
        language_detector: LanguageDetector | None = None,
        framework_detector: FrameworkDetector | None = None,
        dependency_analyzer: DependencyAnalyzer | None = None,
        architecture_detector: ArchitectureDetector | None = None,
        entrypoint_detector: EntrypointDetector | None = None,
        statistics: StatisticsCalculator | None = None,
        report_builder: ProjectAnalysisReportBuilder | None = None,
    ) -> None:
        self._scanner = scanner or ProjectScanner()
        self._languages = language_detector or LanguageDetector()
        self._frameworks = framework_detector or FrameworkDetector()
        self._dependencies = dependency_analyzer or DependencyAnalyzer()
        self._architecture = architecture_detector or ArchitectureDetector()
        self._entrypoints = entrypoint_detector or EntrypointDetector()
        self._statistics = statistics or StatisticsCalculator()
        self._report_builder = report_builder or ProjectAnalysisReportBuilder()

    def analyze(
        self,
        project_path: Path,
        *,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> ProjectAnalysis:
        scanned = self._scanner.scan(project_path)
        languages = self._languages.detect(scanned)
        dependencies = self._dependencies.analyze(scanned)
        frameworks = self._frameworks.detect(scanned, dependencies)
        entrypoints = self._entrypoints.detect(scanned)
        modules = self._modules(scanned)
        package_managers = self._package_managers(scanned)
        architecture = self._architecture.detect(
            scanned, frameworks, entrypoints
        )
        statistics = self._statistics.calculate(
            scanned, languages, modules, entrypoints, dependencies
        )
        return self._report_builder.build(
            scanned=scanned,
            languages=languages,
            frameworks=frameworks,
            package_managers=package_managers,
            modules=modules,
            entrypoints=entrypoints,
            architecture=architecture,
            dependencies=dependencies,
            statistics=statistics,
            metadata=metadata,
        )

    @staticmethod
    def _modules(
        scanned: ScannedProject,
    ) -> tuple[ProjectModule, ...]:
        candidates = {
            path.parts[0]
            for path in scanned.directories
            if path.parts and path.parts[0] not in {"tests", "docs"}
        }
        for item in scanned.files:
            if item.path.parent == Path(".") and item.path.suffix.lower() in {
                ".py",
                ".js",
                ".ts",
                ".java",
                ".kt",
                ".cs",
                ".go",
                ".rs",
                ".php",
                ".rb",
            }:
                candidates.add(item.path.stem)
        return tuple(
            ProjectModule(name=name, path=Path(name))
            for name in sorted(candidates)
        )

    @staticmethod
    def _package_managers(
        scanned: ScannedProject,
    ) -> tuple[PackageManagerDetection, ...]:
        detected = {
            (manager, item.path)
            for item in scanned.files
            if (
                manager := _PACKAGE_MANAGERS.get(item.path.name.lower())
            )
            is not None
        }
        return tuple(
            PackageManagerDetection(name=name, manifest=manifest)
            for name, manifest in sorted(
                detected, key=lambda item: (item[0], item[1].as_posix())
            )
        )


__all__ = ["ProjectAnalyzer"]
