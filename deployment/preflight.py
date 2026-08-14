"""Read-only-oriented production runtime preflight for an ASEP release."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable, Mapping

MINIMUM_PYTHON = (3, 12)
MINIMUM_NODE = (20, 9)
MINIMUM_NPM = (10, 0)


def _version(value: str) -> tuple[int, ...] | None:
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", value)
    return tuple(int(part) for part in match.groups(default="0")) if match else None


def _command_version(executable: str) -> tuple[int, ...] | None:
    allowed = {name: value for name, value in os.environ.items() if name.upper() in {
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
    }}
    completed = subprocess.run(
        (executable, "--version"), capture_output=True, check=False,
        text=True, timeout=10, env=allowed,
    )
    if completed.returncode != 0:
        return None
    return _version(completed.stdout or completed.stderr)


def _usable_directory(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.R_OK | os.W_OK | os.X_OK)


def check(
    environ: Mapping[str, str] | None = None,
    *,
    which: Callable[[str], str | None] = shutil.which,
    command_version: Callable[[str], tuple[int, ...] | None] = _command_version,
    platform_name: str | None = None,
    python_version: tuple[int, ...] | None = None,
) -> tuple[str, ...]:
    """Return safe diagnostic messages; an empty tuple means success."""
    source = os.environ if environ is None else environ
    failures: list[str] = []
    platform_name = platform_name or os.name
    if platform_name not in {"nt", "posix"}:
        failures.append("The operating system is not supported.")

    if (python_version or sys.version_info[:2]) < MINIMUM_PYTHON:
        failures.append("Python 3.12 or newer is required.")

    for name, minimum in (("node", MINIMUM_NODE), ("npm", MINIMUM_NPM)):
        executable = which(name)
        observed = command_version(executable) if executable else None
        if observed is None or observed < minimum:
            failures.append(f"{name} {minimum[0]}.{minimum[1]} or newer is required.")

    codex = which("codex")
    if codex is None or command_version(codex) is None:
        failures.append("Codex CLI must be available through PATH and report a version.")

    if source.get("ASEP_ENVIRONMENT") != "production":
        failures.append("ASEP_ENVIRONMENT must be production.")
    if source.get("ASEP_STORAGE_BACKEND") != "sqlite":
        failures.append("ASEP_STORAGE_BACKEND must be sqlite.")

    database_value = source.get("ASEP_SQLITE_DATABASE", "")
    hosted_value = source.get("ASEP_HOSTED_ROOT", "")
    database = Path(database_value) if database_value else None
    hosted = Path(hosted_value) if hosted_value else None
    if database is None or not database.is_absolute() or not _usable_directory(database.parent):
        failures.append("ASEP_SQLITE_DATABASE must be absolute with an accessible parent directory.")
    elif database.exists() and not os.access(database, os.R_OK | os.W_OK):
        failures.append("ASEP_SQLITE_DATABASE is not readable and writable.")
    if hosted is None or not hosted.is_absolute() or not _usable_directory(hosted):
        failures.append("ASEP_HOSTED_ROOT must be an absolute accessible directory.")

    release = Path(source.get("ASEP_RELEASE_ROOT", "/opt/asep/current"))
    build = release / "frontend" / ".next" / "BUILD_ID"
    if not build.is_file():
        failures.append("The production frontend build is missing.")

    if platform_name == "nt":
        codex_home = Path(source.get("CODEX_HOME", "")) if source.get("CODEX_HOME") else None
        maintenance = Path(source.get("ASEP_MAINTENANCE_DIRECTORY", "")) if source.get("ASEP_MAINTENANCE_DIRECTORY") else None
        for label, directory in (("CODEX_HOME", codex_home), ("ASEP_MAINTENANCE_DIRECTORY", maintenance)):
            if directory is None or not directory.is_absolute() or not _usable_directory(directory):
                failures.append(f"{label} must be an absolute accessible directory on Windows.")
        python = release / ".venv" / "Scripts" / "python.exe"
        if not python.is_file():
            failures.append("The prepared Windows release Python executable is missing.")

    try:
        from asep.configuration import Configuration
        from asep.api.composition import create_default_app

        Configuration.load(source)
        if not callable(create_default_app):
            failures.append("The backend application factory is unavailable.")
    except Exception as exc:  # configuration/import boundary; never echo values
        failures.append(f"Backend production configuration/import failed ({type(exc).__name__}).")

    return tuple(failures)


def main() -> int:
    failures = check()
    if failures:
        print("ASEP production preflight failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("ASEP production preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
