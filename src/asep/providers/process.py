"""Execução portátil de processos, isolada dos providers concretos."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol


class ProcessRunnerError(Exception):
    """Falha interna e independente de plataforma ao executar um processo."""


class ProcessExecutableNotFoundError(ProcessRunnerError):
    pass


class ProcessTimeoutError(ProcessRunnerError):
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        super().__init__(f"processo excedeu {timeout:g} segundos")


class ProcessInterruptedError(ProcessRunnerError):
    pass


class ProcessStartError(ProcessRunnerError):
    def __init__(self, error_type: str) -> None:
        self.error_type = error_type
        super().__init__(f"falha ao iniciar processo: {error_type}")


@dataclass(frozen=True, slots=True)
class ProcessResult:
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str


class ProcessRunnerProtocol(Protocol):
    def is_available(self, executable: str) -> bool: ...

    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str,
        timeout: float,
        working_directory: Path | None,
        environment: Mapping[str, str],
        encoding: str,
    ) -> ProcessResult: ...


class ProcessRunner:
    _HOST_ENVIRONMENT_ALLOWLIST = frozenset({
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
        "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE",
    })
    """Adaptador mínimo sobre subprocess, sem regras de provider."""

    def is_available(self, executable: str) -> bool:
        return shutil.which(executable) is not None

    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str,
        timeout: float,
        working_directory: Path | None,
        environment: Mapping[str, str],
        encoding: str,
    ) -> ProcessResult:
        process_environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in self._HOST_ENVIRONMENT_ALLOWLIST
        }
        process_environment.update(environment)
        try:
            completed = subprocess.run(
                command,
                input=input_text,
                capture_output=True,
                check=False,
                cwd=working_directory,
                env=process_environment,
                timeout=timeout,
                text=True,
                encoding=encoding,
                errors="replace",
                shell=False,
            )
        except FileNotFoundError as exc:
            raise ProcessExecutableNotFoundError from exc
        except subprocess.TimeoutExpired as exc:
            raise ProcessTimeoutError(timeout) from exc
        except KeyboardInterrupt as exc:
            raise ProcessInterruptedError from exc
        except OSError as exc:
            raise ProcessStartError(type(exc).__name__) from exc
        return ProcessResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
