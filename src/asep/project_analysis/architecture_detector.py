"""Inferência arquitetural baseada somente em evidências observáveis."""

from __future__ import annotations

from asep.project_analysis.models import (
    ArchitectureDetection,
    Entrypoint,
    FrameworkDetection,
    ScannedProject,
)


class ArchitectureDetector:
    def detect(
        self,
        scanned: ScannedProject,
        frameworks: tuple[FrameworkDetection, ...],
        entrypoints: tuple[Entrypoint, ...],
    ) -> tuple[ArchitectureDetection, ...]:
        directory_names = {
            path.name.lower() for path in scanned.directories
        }
        file_names = {item.path.name.lower() for item in scanned.files}
        framework_names = {item.name for item in frameworks}
        found: dict[str, set[str]] = {}

        def add(name: str, *evidence: str) -> None:
            found.setdefault(name, set()).update(evidence)

        if {"models", "views", "controllers"} <= directory_names:
            add("MVC", "directories:models,views,controllers")
        if {"domain", "application", "infrastructure"} <= directory_names:
            add(
                "Clean Architecture",
                "directories:domain,application,infrastructure",
            )
        if "ports" in directory_names and "adapters" in directory_names:
            add("Hexagonal", "directories:ports,adapters")
        if "domain" in directory_names and {
            "infrastructure",
            "presentation",
        } & directory_names:
            add("Onion", "directory:domain")
        if framework_names & {"FastAPI", "Flask", "Django", "Express"}:
            add("REST API", "framework:web-api")
        if framework_names & {
            "React",
            "Next.js",
            "Vue",
            "Angular",
            "Streamlit",
        }:
            add("Web Application", "framework:web")
        if "pyproject.toml" in file_names and not entrypoints:
            add("Library", "manifest:pyproject.toml")
        if any(
            item.path.name.lower() in {"__main__.py", "main.py"}
            for item in entrypoints
        ) or "typer" in framework_names:
            add("CLI", "entrypoint:python")
        if any(
            item.path.suffix.lower() in {".csproj", ".sln"}
            for item in scanned.files
        ):
            add("Desktop", "manifest:.NET")
        if not found:
            add("Monolith", "single-project-tree")
        elif len(scanned.files) > 0:
            add("Monolith", "single-project-tree")
        return tuple(
            ArchitectureDetection(
                name=name, evidence=tuple(sorted(evidence))
            )
            for name, evidence in sorted(found.items())
        )


__all__ = ["ArchitectureDetector"]
