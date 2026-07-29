from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pytest

from asep.execution_package import ExecutionPackage
from asep.providers import (
    AgentExecutionStatus,
    AgentProvider,
    CodexProvider,
    CodexProviderConfig,
    ProviderExecutionError,
    ProviderProtocolError,
    ProviderUnavailableError,
)
from asep.providers.process import (
    ProcessExecutableNotFoundError,
    ProcessInterruptedError,
    ProcessResult,
    ProcessStartError,
    ProcessTimeoutError,
)
from tests.test_execution_package import package


class FakeProcessRunner:
    def __init__(
        self,
        result: ProcessResult | None = None,
        *,
        available: bool = True,
        error: BaseException | None = None,
    ) -> None:
        self.result = result or ProcessResult(
            command=("codex", "exec", "-"),
            exit_code=0,
            stdout="Execution completed.",
            stderr="",
        )
        self.available = available
        self.error = error
        self.availability_checks: list[str] = []
        self.calls: list[dict[str, object]] = []

    def is_available(self, executable: str) -> bool:
        self.availability_checks.append(executable)
        return self.available

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
        self.calls.append(
            {
                "command": command,
                "input_text": input_text,
                "timeout": timeout,
                "working_directory": working_directory,
                "environment": dict(environment),
                "encoding": encoding,
            }
        )
        if self.error is not None:
            raise self.error
        return self.result


def configured_provider(
    runner: FakeProcessRunner,
    tmp_path: Path,
) -> CodexProvider:
    return CodexProvider(
        CodexProviderConfig(
            executable="custom-codex",
            timeout=42,
            working_directory=tmp_path,
            environment={"ASEP_TEST": "true"},
            provider_version="1.2.3",
        ),
        process_runner=runner,
    )


def test_codex_provider_conforms_to_agent_provider_and_builds_command(
    tmp_path: Path,
) -> None:
    runner = FakeProcessRunner()
    provider: AgentProvider = configured_provider(runner, tmp_path)

    result = provider.execute(package())

    assert isinstance(provider, CodexProvider)
    assert runner.availability_checks == ["custom-codex"]
    assert runner.calls == [
        {
            "command": ("custom-codex", "exec", "-"),
            "input_text": runner.calls[0]["input_text"],
            "timeout": 42.0,
            "working_directory": tmp_path,
            "environment": {"ASEP_TEST": "true"},
            "encoding": "utf-8",
        }
    ]
    assert result.status is AgentExecutionStatus.SUCCESS
    assert result.provider_name == "codex"
    assert result.provider_version == "1.2.3"


def test_provider_consumes_canonical_execution_package_files(
    tmp_path: Path,
) -> None:
    runner = FakeProcessRunner()
    provider = configured_provider(runner, tmp_path)

    provider.execute(package())

    process_input = str(runner.calls[0]["input_text"])
    for name in (
        "task.md",
        "manifest.yaml",
        "context.json",
        "constraints.md",
    ):
        assert f"--- BEGIN ASEP FILE: {name} ---" in process_input
        assert f"--- END ASEP FILE: {name} ---" in process_input
    assert "# Tarefa" in process_input
    assert '"stage"' in process_input
    assert "prompt_checksum:" in process_input
    assert "Não fazer commit." in process_input


def test_parser_maps_success_and_preserves_progress_stderr(
    tmp_path: Path,
) -> None:
    runner = FakeProcessRunner(
        ProcessResult(
            command=("codex", "exec", "-"),
            exit_code=0,
            stdout="done\n",
            stderr="diagnostic\n",
        )
    )

    result = configured_provider(runner, tmp_path).execute(package())

    assert result.status is AgentExecutionStatus.SUCCESS
    assert result.exit_code == 0
    assert result.stdout == "done\n"
    assert result.stderr == "diagnostic\n"
    assert result.warnings == ()
    assert result.produced_files == ()


def test_parser_maps_nonzero_exit_code_to_failed_result(
    tmp_path: Path,
) -> None:
    runner = FakeProcessRunner(
        ProcessResult(
            command=("codex", "exec", "-"),
            exit_code=7,
            stdout="partial output",
            stderr="execution failed",
        )
    )

    result = configured_provider(runner, tmp_path).execute(package())

    assert result.status is AgentExecutionStatus.FAILED
    assert result.exit_code == 7
    assert result.errors == ("execution failed",)


def test_parser_maps_cancelled_process_to_cancelled_result(
    tmp_path: Path,
) -> None:
    runner = FakeProcessRunner(
        ProcessResult(
            command=("codex", "exec", "-"),
            exit_code=-2,
            stdout="",
            stderr="cancelled",
        )
    )

    result = configured_provider(runner, tmp_path).execute(package())

    assert result.status is AgentExecutionStatus.CANCELLED
    assert result.errors == ("cancelled",)


def test_empty_stdout_is_a_protocol_error(tmp_path: Path) -> None:
    runner = FakeProcessRunner(
        ProcessResult(
            command=("codex", "exec", "-"),
            exit_code=0,
            stdout=" \n",
            stderr="",
        )
    )

    with pytest.raises(ProviderProtocolError, match="sem produzir saída"):
        configured_provider(runner, tmp_path).execute(package())


def test_unavailable_provider_does_not_start_process(
    tmp_path: Path,
) -> None:
    runner = FakeProcessRunner(available=False)
    provider = configured_provider(runner, tmp_path)

    assert provider.is_available() is False
    with pytest.raises(
        ProviderUnavailableError, match="custom-codex"
    ):
        provider.execute(package())
    assert runner.calls == []


def test_file_not_found_during_start_is_provider_unavailable(
    tmp_path: Path,
) -> None:
    runner = FakeProcessRunner(error=ProcessExecutableNotFoundError())

    with pytest.raises(ProviderUnavailableError) as captured:
        configured_provider(runner, tmp_path).execute(package())

    assert isinstance(
        captured.value.__cause__, ProcessExecutableNotFoundError
    )


def test_timeout_is_provider_execution_error(tmp_path: Path) -> None:
    timeout = ProcessTimeoutError(42)
    runner = FakeProcessRunner(error=timeout)

    with pytest.raises(
        ProviderExecutionError, match="timeout de 42 segundos"
    ) as captured:
        configured_provider(runner, tmp_path).execute(package())

    assert captured.value.__cause__ is timeout


def test_interruption_is_provider_execution_error(tmp_path: Path) -> None:
    runner = FakeProcessRunner(error=ProcessInterruptedError())

    with pytest.raises(
        ProviderExecutionError, match="interrompida"
    ):
        configured_provider(runner, tmp_path).execute(package())


def test_os_error_is_provider_execution_error(tmp_path: Path) -> None:
    runner = FakeProcessRunner(error=ProcessStartError("PermissionError"))

    with pytest.raises(
        ProviderExecutionError, match="PermissionError"
    ):
        configured_provider(runner, tmp_path).execute(package())


def test_config_is_strict_typed_and_environment_is_defensively_copied(
    tmp_path: Path,
) -> None:
    environment = {"TOKEN": "redacted"}
    config = CodexProviderConfig(
        working_directory=tmp_path,
        environment=environment,
    )
    environment["TOKEN"] = "changed"

    assert config.working_directory == tmp_path
    assert config.environment["TOKEN"] == "redacted"
    with pytest.raises(TypeError):
        config.environment["NEW"] = "value"  # type: ignore[index]


def test_provider_public_api_exports_codex_types() -> None:
    import asep.providers as providers

    assert providers.CodexProvider is CodexProvider
    assert providers.CodexProviderConfig is CodexProviderConfig
