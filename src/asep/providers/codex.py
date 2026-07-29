"""Provider concreto para execução não interativa do Codex CLI."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)

from asep.execution_package import (
    ExecutionPackage,
    ExecutionPackageSerializer,
)
from asep.providers.errors import (
    ProviderExecutionError,
    ProviderUnavailableError,
)
from asep.providers.models import AgentExecutionResult
from asep.providers.parser import CodexResultParser
from asep.providers.process import (
    ProcessExecutableNotFoundError,
    ProcessInterruptedError,
    ProcessRunner,
    ProcessRunnerProtocol,
    ProcessStartError,
    ProcessTimeoutError,
)

_CONSUMED_PACKAGE_FILES = (
    "task.md",
    "manifest.yaml",
    "context.json",
    "constraints.md",
)


class CodexProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    executable: str = "codex"
    timeout: float = Field(default=600.0, gt=0)
    working_directory: Path | None = None
    environment: Mapping[str, str] = Field(default_factory=dict)
    encoding: str = "utf-8"
    provider_version: str = "unknown"

    @field_validator("executable", "encoding", "provider_version")
    @classmethod
    def text_configuration_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("configuração textual não pode ser vazia")
        return value

    @field_validator("environment")
    @classmethod
    def environment_is_immutable(
        cls, value: Mapping[str, str]
    ) -> Mapping[str, str]:
        return MappingProxyType(dict(value))

    @field_serializer("environment")
    def serialize_environment(
        self, value: Mapping[str, str]
    ) -> dict[str, str]:
        return dict(value)


class CodexProvider:
    name = "codex"

    def __init__(
        self,
        config: CodexProviderConfig | None = None,
        *,
        process_runner: ProcessRunnerProtocol | None = None,
        parser: CodexResultParser | None = None,
        serializer: ExecutionPackageSerializer | None = None,
    ) -> None:
        self._config = config or CodexProviderConfig()
        self._process_runner = process_runner or ProcessRunner()
        self._parser = parser or CodexResultParser()
        self._serializer = serializer or ExecutionPackageSerializer()

    def is_available(self) -> bool:
        return self._process_runner.is_available(self._config.executable)

    def execute(self, package: ExecutionPackage) -> AgentExecutionResult:
        if not self.is_available():
            raise ProviderUnavailableError(
                f"Executável do Codex indisponível: "
                f"{self._config.executable}"
            )

        command = (self._config.executable, "exec", "-")
        try:
            process_result = self._process_runner.run(
                command,
                input_text=self._execution_input(package),
                timeout=self._config.timeout,
                working_directory=self._config.working_directory,
                environment=self._config.environment,
                encoding=self._config.encoding,
            )
        except ProcessExecutableNotFoundError as exc:
            raise ProviderUnavailableError(
                f"Executável do Codex indisponível: "
                f"{self._config.executable}"
            ) from exc
        except ProcessTimeoutError as exc:
            raise ProviderExecutionError(
                f"Execução do Codex excedeu o timeout de "
                f"{self._config.timeout:g} segundos."
            ) from exc
        except ProcessInterruptedError as exc:
            raise ProviderExecutionError(
                "Execução do Codex interrompida."
            ) from exc
        except ProcessStartError as exc:
            raise ProviderExecutionError(
                f"Falha ao iniciar o processo Codex: {exc.error_type}."
            ) from exc

        return self._parser.parse(
            process_result,
            provider_name=self.name,
            provider_version=self._config.provider_version,
        )

    def _execution_input(self, package: ExecutionPackage) -> str:
        serialized = {
            item.name: item.content.decode("utf-8")
            for item in self._serializer.serialize(package)
        }
        sections = []
        for name in _CONSUMED_PACKAGE_FILES:
            sections.append(
                f"--- BEGIN ASEP FILE: {name} ---\n"
                f"{serialized[name].rstrip()}\n"
                f"--- END ASEP FILE: {name} ---"
            )
        return "\n\n".join(sections) + "\n"
