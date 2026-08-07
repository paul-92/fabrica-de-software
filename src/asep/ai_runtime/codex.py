"""Adapter do Codex CLI oficial para a porta provider-agnostic AIRuntime."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.ai_runtime.contracts import AIRuntimeRegistry
from asep.ai_runtime.errors import (
    AIRuntimeAuthenticationError,
    AIRuntimeConfigurationError,
    AIRuntimeRateLimitError,
    AIRuntimeTimeoutError,
    AIRuntimeUnavailableError,
    AIRuntimeUnexpectedError,
)
from asep.ai_runtime.models import (
    AIRuntimeCapability,
    AIRuntimeIdentity,
    AIRuntimeExecutionMode,
    AIRuntimeRequest,
    AIRuntimeResult,
)
from asep.ai_runtime.parser import CodexJSONLParser
from asep.ai_runtime.registry import InMemoryAIRuntimeRegistry
from asep.providers.process import (
    ProcessExecutableNotFoundError,
    ProcessInterruptedError,
    ProcessRunner,
    ProcessRunnerProtocol,
    ProcessStartError,
    ProcessTimeoutError,
)


class CodexAIRuntimeConfig(BaseModel):
    """Configuração explícita e imutável do adapter local."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace: Path
    executable: str = "codex"
    timeout: float = Field(default=600.0, gt=0)
    model_id: str = "codex-default"
    encoding: str = "utf-8"

    @field_validator("workspace")
    @classmethod
    def workspace_is_explicit_and_valid(cls, value: Path) -> Path:
        resolved = value.expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError("workspace deve existir e ser diretório")
        return resolved

    @field_validator("executable", "model_id", "encoding")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("configuração textual não pode ser vazia")
        return normalized


class CodexAIRuntime:
    """Executa intenções ASEP através de ``codex exec`` oficial."""

    def __init__(
        self,
        config: CodexAIRuntimeConfig,
        *,
        process_runner: ProcessRunnerProtocol | None = None,
        parser: CodexJSONLParser | None = None,
    ) -> None:
        self._config = config
        self._process_runner = process_runner or ProcessRunner()
        self._parser = parser or CodexJSONLParser()
        self._identity = AIRuntimeIdentity(
            runtime_id="codex",
            model_id=config.model_id,
            capabilities=(
                AIRuntimeCapability(id="text-generation"),
                AIRuntimeCapability(id="code-reasoning"),
            ),
        )

    @property
    def identity(self) -> AIRuntimeIdentity:
        return self._identity

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        if not self._process_runner.is_available(self._config.executable):
            raise AIRuntimeUnavailableError(self.identity.runtime_id)

        try:
            result = self._process_runner.run(
                self._command(request.execution_mode),
                input_text=self._input(request),
                timeout=self._config.timeout,
                working_directory=request.workspace or self._config.workspace,
                environment={},
                encoding=self._config.encoding,
            )
        except ProcessExecutableNotFoundError as exc:
            raise AIRuntimeUnavailableError(self.identity.runtime_id) from exc
        except ProcessTimeoutError as exc:
            raise AIRuntimeTimeoutError(self.identity.runtime_id) from exc
        except (ProcessInterruptedError, ProcessStartError) as exc:
            raise AIRuntimeUnexpectedError(self.identity.runtime_id, exc) from exc

        if result.exit_code != 0:
            self._raise_process_failure(result.stderr)
        return self._parser.parse(result.stdout, identity=self.identity)

    def _command(
        self, execution_mode: AIRuntimeExecutionMode
    ) -> tuple[str, ...]:
        sandbox = {
            AIRuntimeExecutionMode.READ_ONLY: "read-only",
            AIRuntimeExecutionMode.WORKSPACE_WRITE: "workspace-write",
        }[execution_mode]
        return (
            self._config.executable,
            "exec",
            "--json",
            "--ephemeral",
            "--sandbox",
            sandbox,
            "--skip-git-repo-check",
            "-",
        )

    @staticmethod
    def _input(request: AIRuntimeRequest) -> str:
        payload = request.model_dump(mode="json")
        return (
            f"{payload['instruction']}\n\n"
            "ASEP context (JSON):\n"
            f"{json.dumps(payload['context'], sort_keys=True, ensure_ascii=False)}\n\n"
            "ASEP metadata (JSON):\n"
            f"{json.dumps(payload['metadata'], sort_keys=True, ensure_ascii=False)}\n"
        )

    def _raise_process_failure(self, stderr: str) -> None:
        normalized = stderr.casefold()
        if any(
            marker in normalized
            for marker in ("not logged in", "authentication", "unauthorized", "401")
        ):
            raise AIRuntimeAuthenticationError(self.identity.runtime_id)
        if "rate limit" in normalized or "429" in normalized:
            raise AIRuntimeRateLimitError(self.identity.runtime_id)
        if "config" in normalized:
            raise AIRuntimeConfigurationError(self.identity.runtime_id)
        raise AIRuntimeUnexpectedError(
            self.identity.runtime_id,
            RuntimeError("Codex process failed"),
        )


def create_codex_ai_runtime_registry(
    config: CodexAIRuntimeConfig,
    *,
    process_runner: ProcessRunnerProtocol | None = None,
) -> AIRuntimeRegistry:
    """Compõe explicitamente um registry contendo somente o Codex runtime."""

    registry = InMemoryAIRuntimeRegistry()
    registry.register(
        CodexAIRuntime(config, process_runner=process_runner)
    )
    return registry


__all__ = [
    "CodexAIRuntime",
    "CodexAIRuntimeConfig",
    "create_codex_ai_runtime_registry",
]
