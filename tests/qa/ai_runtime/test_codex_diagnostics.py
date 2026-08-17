from pathlib import Path
from typing import Mapping

import pytest

from asep.ai_runtime import (
    AIRuntimeConnectionState,
    CodexAIRuntimeDiagnostics,
    CodexDiagnosticsConfig,
)
from asep.providers.process import ProcessResult, ProcessTimeoutError


class Runner:
    def __init__(self, *, available=True, auth="Logged in using ChatGPT", error=None):
        self.available = available
        self.auth = auth
        self.error = error
        self.calls: list[tuple[str, ...]] = []

    def is_available(self, executable: str) -> bool:
        return self.available

    def run(self, command: tuple[str, ...], *, input_text: str, timeout: float,
            working_directory: Path | None, environment: Mapping[str, str],
            encoding: str) -> ProcessResult:
        self.calls.append(command)
        if self.error:
            raise self.error
        is_version = command[-1] == "--version"
        output = "codex-cli 1.2.3" if is_version else self.auth
        code = 0 if is_version or "Not logged in" not in self.auth else 1
        return ProcessResult(command, code, output, "")


def diagnostics(tmp_path: Path, runner: Runner) -> CodexAIRuntimeDiagnostics:
    return CodexAIRuntimeDiagnostics(
        CodexDiagnosticsConfig(working_directory=tmp_path),
        process_runner=runner,
    )


def test_not_installed_does_not_start_process(tmp_path: Path) -> None:
    runner = Runner(available=False)
    status = diagnostics(tmp_path, runner).status()
    assert status.state is AIRuntimeConnectionState.NOT_INSTALLED
    assert not status.installed and not status.ready
    assert runner.calls == []


def test_ready_detects_version_and_authentication(tmp_path: Path) -> None:
    status = diagnostics(tmp_path, Runner()).status()
    assert status.state is AIRuntimeConnectionState.READY
    assert status.installed and status.authenticated and status.ready
    assert status.version == "1.2.3"
    assert status.authentication_command is None


def test_not_authenticated_returns_only_official_instruction(tmp_path: Path) -> None:
    status = diagnostics(tmp_path, Runner(auth="Not logged in")).status()
    assert status.state is AIRuntimeConnectionState.NOT_AUTHENTICATED
    assert status.installed and not status.authenticated and not status.ready
    assert status.authentication_command == "codex login"


def test_resolved_windows_wrapper_is_installed_and_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved = str(tmp_path / "codex.CMD")
    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr("asep.providers.process.shutil.which", lambda _: resolved)

    class Completed:
        returncode = 0
        stderr = ""

        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_run(command: tuple[str, ...], **kwargs: object) -> Completed:
        commands.append(command)
        return Completed(
            "codex-cli 0.147.0"
            if command[-1] == "--version"
            else "Logged in using ChatGPT"
        )

    monkeypatch.setattr("asep.providers.process.subprocess.run", fake_run)

    status = CodexAIRuntimeDiagnostics(
        CodexDiagnosticsConfig(working_directory=tmp_path)
    ).status()

    assert status.state is AIRuntimeConnectionState.READY
    assert status.installed and status.authenticated and status.ready
    assert status.version == "0.147.0"
    assert commands == [
        (resolved, "--version"),
        (resolved, "login", "status"),
    ]


@pytest.mark.parametrize("error", [ProcessTimeoutError(10)])
def test_failure_is_sanitized(tmp_path: Path, error: Exception) -> None:
    status = diagnostics(tmp_path, Runner(error=error)).status()
    serialized = status.model_dump_json().casefold()
    assert status.state is AIRuntimeConnectionState.ERROR
    for secret in ("access_token", "refresh_token", "cookie", "authorization", "api key"):
        assert secret not in serialized
