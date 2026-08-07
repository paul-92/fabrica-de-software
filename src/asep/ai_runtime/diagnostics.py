"""Diagnóstico seguro de disponibilidade de AI Runtimes."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from asep.providers.process import (
    ProcessExecutableNotFoundError,
    ProcessInterruptedError,
    ProcessRunner,
    ProcessRunnerProtocol,
    ProcessStartError,
    ProcessTimeoutError,
)


class AIRuntimeConnectionState(StrEnum):
    NOT_INSTALLED = "not_installed"
    NOT_AUTHENTICATED = "not_authenticated"
    READY = "ready"
    ERROR = "error"


class AIRuntimeConnectionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_id: str
    installed: bool
    authenticated: bool
    ready: bool
    state: AIRuntimeConnectionState
    version: str | None = None
    message: str
    authentication_command: str | None = None

    @field_validator("runtime_id", "message")
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("texto obrigatório não pode ser vazio")
        return value

    @model_validator(mode="after")
    def flags_match_state(self) -> AIRuntimeConnectionStatus:
        expected_ready = (
            self.state is AIRuntimeConnectionState.READY
            and self.installed
            and self.authenticated
        )
        if self.ready != expected_ready:
            raise ValueError("ready deve refletir o estado da conexão")
        return self


@runtime_checkable
class AIRuntimeDiagnostics(Protocol):
    runtime_id: str

    def status(self) -> AIRuntimeConnectionStatus: ...


class CodexDiagnosticsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    working_directory: Path
    executable: str = "codex"
    timeout: float = Field(default=10.0, gt=0)
    encoding: str = "utf-8"

    @field_validator("working_directory")
    @classmethod
    def directory_is_valid(cls, value: Path) -> Path:
        resolved = value.expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError("working_directory deve existir e ser diretório")
        return resolved


class CodexAIRuntimeDiagnostics:
    """Usa somente comandos oficiais e nunca acessa credential stores."""

    runtime_id = "codex"

    def __init__(
        self,
        config: CodexDiagnosticsConfig,
        *,
        process_runner: ProcessRunnerProtocol | None = None,
    ) -> None:
        self._config = config
        self._runner = process_runner or ProcessRunner()

    def status(self) -> AIRuntimeConnectionStatus:
        if not self._runner.is_available(self._config.executable):
            return self._status(AIRuntimeConnectionState.NOT_INSTALLED)
        try:
            version_result = self._run((self._config.executable, "--version"))
            version = self._version(version_result.stdout)
            if version_result.exit_code != 0 or version is None:
                return self._status(AIRuntimeConnectionState.ERROR)
            auth_result = self._run(
                (self._config.executable, "login", "status")
            )
        except ProcessExecutableNotFoundError:
            return self._status(AIRuntimeConnectionState.NOT_INSTALLED)
        except ProcessTimeoutError:
            return self._status(
                AIRuntimeConnectionState.ERROR,
                message="Codex diagnostics timed out.",
            )
        except (ProcessInterruptedError, ProcessStartError):
            return self._status(AIRuntimeConnectionState.ERROR)

        auth_output = f"{auth_result.stdout}\n{auth_result.stderr}".casefold()
        if auth_result.exit_code == 0 and "logged in" in auth_output:
            return self._status(AIRuntimeConnectionState.READY, version=version)
        if "not logged in" in auth_output or "not authenticated" in auth_output:
            return self._status(
                AIRuntimeConnectionState.NOT_AUTHENTICATED,
                version=version,
            )
        return self._status(AIRuntimeConnectionState.ERROR, version=version)

    def _run(self, command: tuple[str, ...]):
        return self._runner.run(
            command,
            input_text="",
            timeout=self._config.timeout,
            working_directory=self._config.working_directory,
            environment={},
            encoding=self._config.encoding,
        )

    @staticmethod
    def _version(output: str) -> str | None:
        normalized = output.strip()
        if not normalized or "\n" in normalized or "\r" in normalized:
            return None
        return normalized.removeprefix("codex-cli ").strip() or None

    def _status(
        self,
        state: AIRuntimeConnectionState,
        *,
        version: str | None = None,
        message: str | None = None,
    ) -> AIRuntimeConnectionStatus:
        messages = {
            AIRuntimeConnectionState.NOT_INSTALLED: "Codex is not installed.",
            AIRuntimeConnectionState.NOT_AUTHENTICATED: "Codex is not connected.",
            AIRuntimeConnectionState.READY: "Codex is ready.",
            AIRuntimeConnectionState.ERROR: "Codex status is unavailable.",
        }
        installed = state is not AIRuntimeConnectionState.NOT_INSTALLED
        authenticated = state is AIRuntimeConnectionState.READY
        return AIRuntimeConnectionStatus(
            runtime_id=self.runtime_id,
            installed=installed,
            authenticated=authenticated,
            ready=state is AIRuntimeConnectionState.READY,
            state=state,
            version=version,
            message=message or messages[state],
            authentication_command=(
                "codex login"
                if state is AIRuntimeConnectionState.NOT_AUTHENTICATED
                else None
            ),
        )


__all__ = [
    "AIRuntimeConnectionState",
    "AIRuntimeConnectionStatus",
    "AIRuntimeDiagnostics",
    "CodexAIRuntimeDiagnostics",
    "CodexDiagnosticsConfig",
]
