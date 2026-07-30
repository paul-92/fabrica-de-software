from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.project_analysis import ProjectAnalysis, ProjectAnalyzer
from asep.project_analysis.dependency_analyzer import DependencyAnalyzer
from asep.project_analysis.framework_detector import FrameworkDetector
from asep.project_analysis.models import (
    ArchitectureDetection,
    Entrypoint,
    LanguageStatistics,
    PackageManagerDetection,
    ProjectModule,
    ProjectStatistics,
    ScannedFile,
    ScannedProject,
)
from asep.project_analysis.report_builder import (
    ProjectAnalysisReportBuilder,
)
from asep.project_analysis.scanner import ProjectScanner

NOW = datetime(2026, 7, 30, 18, 0, tzinfo=UTC)


def write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_empty_project_produces_complete_immutable_analysis(
    tmp_path: Path,
) -> None:
    result = ProjectAnalyzer().analyze(tmp_path)

    assert isinstance(result, ProjectAnalysis)
    assert result.root_path == tmp_path.resolve()
    assert result.project_name == tmp_path.name
    assert result.languages == ()
    assert result.frameworks == ()
    assert result.package_managers == ()
    assert result.entrypoints == ()
    assert result.architecture[0].name == "Monolith"
    assert result.statistics.file_count == 0
    with pytest.raises(ValidationError):
        result.project_name = "changed"
    with pytest.raises(TypeError):
        result.metadata["changed"] = True


def test_python_project_detects_language_framework_dependencies_and_cli(
    tmp_path: Path,
) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
[project]
name = "sample"
dependencies = ["fastapi>=0.120", "pydantic==2.13"]
[project.optional-dependencies]
test = ["pytest>=8"]
""",
    )
    write(
        tmp_path / "src/app/main.py",
        "from fastapi import FastAPI\napp = FastAPI()\n",
    )
    write(tmp_path / "tests/test_app.py", "def test_ok():\n    pass\n")
    write(tmp_path / "README.md", "# Sample\n")

    result = ProjectAnalyzer().analyze(tmp_path)

    assert [(item.name, item.file_count) for item in result.languages] == [
        ("Python", 2)
    ]
    assert [item.name for item in result.frameworks] == ["FastAPI"]
    assert {item.name for item in result.dependencies} == {
        "fastapi",
        "pydantic",
        "pytest",
    }
    assert [(item.name, item.manifest.as_posix()) for item in result.package_managers] == [
        ("pip", "pyproject.toml")
    ]
    assert result.entrypoints[0].path.as_posix() == "src/app/main.py"
    assert {"CLI", "REST API", "Monolith"} <= {
        item.name for item in result.architecture
    }
    assert result.statistics.test_file_count == 1
    assert result.statistics.documentation_file_count == 1


def test_next_project_detects_web_stack_and_node_dependencies(
    tmp_path: Path,
) -> None:
    write(
        tmp_path / "package.json",
        json.dumps(
            {
                "dependencies": {"next": "15.0", "react": "^19"},
                "devDependencies": {"typescript": "^5"},
                "peerDependencies": {"react-dom": "^19"},
            }
        ),
    )
    write(tmp_path / "package-lock.json", "{}")
    write(tmp_path / "next.config.js", "module.exports = {}")
    write(tmp_path / "src/main.ts", "import React from 'react'\n")

    result = ProjectAnalyzer().analyze(tmp_path)

    assert {item.name for item in result.languages} == {
        "JavaScript",
        "TypeScript",
    }
    assert {item.name for item in result.frameworks} == {"Next.js", "React"}
    assert {item.name for item in result.package_managers} == {"npm"}
    assert {item.name for item in result.dependencies} == {
        "next",
        "react",
        "typescript",
        "react-dom",
    }
    assert "Web Application" in {
        item.name for item in result.architecture
    }


def test_mixed_project_detects_all_supported_languages_and_entrypoints(
    tmp_path: Path,
) -> None:
    extensions = {
        "main.py": "Python",
        "index.js": "JavaScript",
        "server.ts": "TypeScript",
        "App.java": "Java",
        "App.kt": "Kotlin",
        "App.cs": "C#",
        "main.go": "Go",
        "lib.rs": "Rust",
        "index.php": "PHP",
        "app.rb": "Ruby",
    }
    for filename in extensions:
        write(tmp_path / "src" / filename, "line\n")

    result = ProjectAnalyzer().analyze(tmp_path)

    assert {item.name for item in result.languages} == set(
        extensions.values()
    )
    assert {item.path.name for item in result.entrypoints} == {
        "main.py",
        "index.js",
        "server.ts",
    }
    assert result.statistics.lines_of_code == 10
    assert result.statistics.entrypoint_count == 3


def test_scanner_ignores_hidden_and_default_directories(
    tmp_path: Path,
) -> None:
    write(tmp_path / ".hidden.py", "hidden")
    write(tmp_path / ".secret/visible.py", "hidden")
    write(tmp_path / "node_modules/package/index.js", "ignored")
    write(tmp_path / "src/main.py", "visible")

    scanned = ProjectScanner().scan(tmp_path)

    assert tuple(item.path.as_posix() for item in scanned.files) == (
        "src/main.py",
    )
    assert tuple(path.as_posix() for path in scanned.directories) == (
        "src",
    )
    assert scanned.maximum_depth == 2


def test_scanner_accepts_custom_ignored_directories(
    tmp_path: Path,
) -> None:
    write(tmp_path / "generated/code.py", "")
    write(tmp_path / "node_modules/kept.js", "")

    scanned = ProjectScanner({"generated"}).scan(tmp_path)

    assert [item.path.as_posix() for item in scanned.files] == [
        "node_modules/kept.js"
    ]


def test_scanner_rejects_missing_project(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="não encontrado"):
        ProjectScanner().scan(tmp_path / "missing")


def test_architecture_heuristics_detect_known_directory_shapes(
    tmp_path: Path,
) -> None:
    for directory in (
        "models",
        "views",
        "controllers",
        "domain",
        "application",
        "infrastructure",
        "ports",
        "adapters",
        "presentation",
    ):
        write(tmp_path / directory / "placeholder.txt")

    names = {
        item.name for item in ProjectAnalyzer().analyze(tmp_path).architecture
    }

    assert {"MVC", "Clean Architecture", "Hexagonal", "Onion"} <= names


def test_dependency_analyzer_reads_requirements_and_poetry(
    tmp_path: Path,
) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
[tool.poetry.dependencies]
python = ">=3.12"
flask = { version = "^3" }
requests = "^2"
""",
    )
    write(
        tmp_path / "requirements.txt",
        "# comment\nDjango==5.0\n-r base.txt\nhttps://example.invalid/x\n",
    )
    scanned = ProjectScanner().scan(tmp_path)

    dependencies = DependencyAnalyzer().analyze(scanned)

    by_name = {item.name.lower(): item.version for item in dependencies}
    assert by_name == {
        "django": "==5.0",
        "flask": "^3",
        "requests": "^2",
    }


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("pyproject.toml", "not valid = ["),
        ("package.json", "{"),
        ("package.json", "[]"),
    ],
)
def test_invalid_dependency_manifests_are_ignored(
    tmp_path: Path, filename: str, content: str
) -> None:
    write(tmp_path / filename, content)

    assert DependencyAnalyzer().analyze(ProjectScanner().scan(tmp_path)) == ()


def test_framework_detection_uses_imports_and_known_files(
    tmp_path: Path,
) -> None:
    write(tmp_path / "manage.py")
    write(
        tmp_path / "app.py",
        "from flask import Flask\nimport streamlit\n",
    )
    scanned = ProjectScanner().scan(tmp_path)

    detected = FrameworkDetector().detect(scanned, ())

    assert {item.name for item in detected} == {
        "Django",
        "Flask",
        "Streamlit",
    }


def test_modules_and_statistics_are_deterministic(tmp_path: Path) -> None:
    write(tmp_path / "zeta/module.py", "one\ntwo\n")
    write(tmp_path / "alpha/module.py", "one\n")
    write(tmp_path / "root.py", "one\n")

    first = ProjectAnalyzer().analyze(tmp_path)
    second = ProjectAnalyzer().analyze(tmp_path)

    assert [item.name for item in first.modules] == [
        "alpha",
        "root",
        "zeta",
    ]
    assert first.statistics == second.statistics
    assert first.model_dump(exclude={"generated_at"}) == second.model_dump(
        exclude={"generated_at"}
    )


def test_report_builder_uses_clock_and_metadata(tmp_path: Path) -> None:
    scanned = ScannedProject(root_path=tmp_path.resolve())
    statistics = ProjectStatistics(
        file_count=0,
        directory_count=0,
        lines_of_code=0,
        test_file_count=0,
        documentation_file_count=0,
        maximum_depth=0,
        module_count=0,
        entrypoint_count=0,
        dependency_count=0,
    )

    result = ProjectAnalysisReportBuilder(clock=lambda: NOW).build(
        scanned=scanned,
        languages=(LanguageStatistics(name="Python", file_count=0, line_count=0),),
        frameworks=(),
        package_managers=(
            PackageManagerDetection(name="pip", manifest=Path("pyproject.toml")),
        ),
        modules=(ProjectModule(name="src", path=Path("src")),),
        entrypoints=(Entrypoint(path=Path("main.py"), language="Python"),),
        architecture=(ArchitectureDetection(name="CLI"),),
        dependencies=(),
        statistics=statistics,
        metadata={"source": "test"},
    )

    assert result.generated_at == NOW
    assert result.metadata["source"] == "test"
    assert result.metadata["heuristics_version"] == "1.0"


def test_public_exports_are_intentional() -> None:
    import asep.project_analysis as project_analysis

    assert {"ProjectAnalyzer", "ProjectAnalysis"} <= set(
        project_analysis.__all__
    )
