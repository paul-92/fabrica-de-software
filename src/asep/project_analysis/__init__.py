"""API pública do Project Analyzer determinístico."""

from asep.project_analysis.analyzer import ProjectAnalyzer
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
)

__all__ = [
    "ArchitectureDetection",
    "Dependency",
    "Entrypoint",
    "FrameworkDetection",
    "LanguageStatistics",
    "PackageManagerDetection",
    "ProjectAnalysis",
    "ProjectAnalyzer",
    "ProjectModule",
    "ProjectStatistics",
]
