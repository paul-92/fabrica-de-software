"""Read-only verification of the local ASEP development environment."""

from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path


MINIMUM_PYTHON = (3, 12)
ESSENTIAL_MODULES = (
    "asep",
    "typer",
    "pydantic",
    "yaml",
    "fastapi",
    "uvicorn",
)
REQUIRED_DIRECTORIES = ("src", "tests", "docs")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    failures: list[str] = []

    print(f"Python: {platform.python_version()} ({platform.architecture()[0]})")
    print(f"Platform: {platform.platform()}")

    if sys.version_info < MINIMUM_PYTHON:
        failures.append("Python 3.12 or newer is required.")

    for module_name in ESSENTIAL_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - diagnostic boundary
            failures.append(
                f"Import failed for {module_name}: {type(exc).__name__}: {exc}"
            )

    for directory in REQUIRED_DIRECTORIES:
        if not (root / directory).is_dir():
            failures.append(f"Required directory is missing: {directory}")

    try:
        from asep.configuration import ApplicationSettings

        settings = ApplicationSettings()
        print(f"Default storage backend: {settings.storage_backend}")
        print(f"Default storage directory: {settings.storage_directory}")
    except Exception as exc:  # pragma: no cover - diagnostic boundary
        failures.append(
            f"Default configuration is invalid: {type(exc).__name__}: {exc}"
        )

    if failures:
        print("Environment is not ready:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Environment is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
