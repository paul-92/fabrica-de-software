from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pytest
from pydantic import ValidationError

from asep.ai_runtime import (
    AIRuntime,
    AIRuntimeAuthenticationError,
    AIRuntimeInvalidResponseError,
    AIRuntimeRateLimitError,
    AIRuntimeRequest,
    AIRuntimeTimeoutError,
    AIRuntimeUnavailableError,
    AIRuntimeUnexpectedError,
    CodexAIRuntime,
    CodexAIRuntimeConfig,
    create_codex_ai_runtime_registry,
)
from asep.providers.process import (
    ProcessResult,
    ProcessRunner,
    ProcessStartError,
    ProcessTimeoutError,
)


def jsonl(*events: dict[str, object]) -> str:
    return "\n".join(json.dumps(event) for event in events)


class FakeProcessRunner:
    def __init__(
        self,
        result: ProcessResult | None = None,
        *,
        available: bool = True,
        error: BaseException | None = None,
    ) -> None:
        self.result = result or ProcessResult(
            command=("codex",),
            exit_code=0,
            stdout=jsonl(
                {"type": "thread.started", "thread_id": "thread-1"},
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": "Completed",
                    },
                },
                {
                    "type": "turn.completed",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            ),
            stderr="",
        )
        self.available = available
        self.error = error
        self.calls: list[dict[str, object]] = []

    def is_available(self, executable: str) -> bool:
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


def runtime(
    workspace: Path,
    runner: FakeProcessRunner,
) -> CodexAIRuntime:
    return CodexAIRuntime(
        CodexAIRuntimeConfig(
            workspace=workspace,
            executable="controlled-codex",
            timeout=42,
            model_id="configured-model",
        ),
        process_runner=runner,
    )


def test_runtime_maps_request_to_controlled_codex_exec(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    adapter: AIRuntime = runtime(tmp_path, runner)
    request = AIRuntimeRequest(
        instruction="Analyze this project",
        context={"failure": {"summary": "broken test"}},
        metadata={"correlation_id": "run-1"},
    )

    result = adapter.execute(request)

    assert runner.calls == [
        {
            "command": (
                "controlled-codex",
                "exec",
                "--json",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "-",
            ),
            "input_text": runner.calls[0]["input_text"],
            "timeout": 42.0,
            "working_directory": tmp_path.resolve(),
            "environment": {},
            "encoding": "utf-8",
        }
    ]
    process_input = str(runner.calls[0]["input_text"])
    assert process_input.startswith("Analyze this project")
    assert '"summary": "broken test"' in process_input
    assert '"correlation_id": "run-1"' in process_input
    assert result.output == "Completed"
    assert result.identity.runtime_id == "codex"
    assert result.identity.model_id == "configured-model"


def test_reused_process_runner_never_enables_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command: tuple[str, ...], **kwargs: object) -> Completed:
        captured["command"] = command
        captured.update(kwargs)
        return Completed()

    monkeypatch.setattr("asep.providers.process.subprocess.run", fake_run)

    ProcessRunner().run(
        ("codex", "exec", "-"),
        input_text="instruction",
        timeout=10,
        working_directory=tmp_path,
        environment={},
        encoding="utf-8",
    )

    assert captured["shell"] is False
    assert captured["cwd"] == tmp_path


def test_workspace_must_be_explicit_existing_directory(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="workspace"):
        CodexAIRuntimeConfig(workspace=tmp_path / "missing")


def test_request_workspace_overrides_configured_workspace(tmp_path: Path) -> None:
    configured = tmp_path / "configured"; configured.mkdir()
    project = tmp_path / "project"; project.mkdir()
    runner = FakeProcessRunner()
    runtime(configured, runner).execute(
        AIRuntimeRequest(instruction="test", workspace=project)
    )
    assert runner.calls[0]["working_directory"] == project.resolve()


def test_parser_maps_structured_usage_only_when_present(tmp_path: Path) -> None:
    with_usage = runtime(tmp_path, FakeProcessRunner()).execute(
        AIRuntimeRequest(instruction="test")
    )
    without_usage_runner = FakeProcessRunner(
        ProcessResult(
            command=("codex",),
            exit_code=0,
            stdout=jsonl(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "Done"},
                }
            ),
            stderr="",
        )
    )
    without_usage = runtime(tmp_path, without_usage_runner).execute(
        AIRuntimeRequest(instruction="test")
    )

    assert with_usage.usage is not None
    assert with_usage.usage.input_units == 10
    assert with_usage.usage.output_units == 5
    assert with_usage.usage.total_units == 15
    assert with_usage.usage.cost is None
    assert without_usage.usage is None


@pytest.mark.parametrize("stdout", ["", "not-json", '{"type":"turn.started"}'])
def test_invalid_codex_response_is_rejected(
    tmp_path: Path,
    stdout: str,
) -> None:
    runner = FakeProcessRunner(
        ProcessResult(
            command=("codex",),
            exit_code=0,
            stdout=stdout,
            stderr="",
        )
    )

    with pytest.raises(AIRuntimeInvalidResponseError):
        runtime(tmp_path, runner).execute(AIRuntimeRequest(instruction="test"))


def test_unavailable_codex_never_starts_process(tmp_path: Path) -> None:
    runner = FakeProcessRunner(available=False)

    with pytest.raises(AIRuntimeUnavailableError):
        runtime(tmp_path, runner).execute(AIRuntimeRequest(instruction="test"))

    assert runner.calls == []


def test_timeout_maps_to_provider_agnostic_error(tmp_path: Path) -> None:
    runner = FakeProcessRunner(error=ProcessTimeoutError(42))

    with pytest.raises(AIRuntimeTimeoutError):
        runtime(tmp_path, runner).execute(AIRuntimeRequest(instruction="test"))


@pytest.mark.parametrize(
    ("stderr", "error_type"),
    [
        ("Not logged in. Run codex login.", AIRuntimeAuthenticationError),
        ("Rate limit exceeded", AIRuntimeRateLimitError),
        ("provider crashed", AIRuntimeUnexpectedError),
    ],
)
def test_process_failures_are_safely_classified(
    tmp_path: Path,
    stderr: str,
    error_type: type[Exception],
) -> None:
    runner = FakeProcessRunner(
        ProcessResult(
            command=("codex",),
            exit_code=1,
            stdout="",
            stderr=stderr,
        )
    )

    with pytest.raises(error_type) as caught:
        runtime(tmp_path, runner).execute(AIRuntimeRequest(instruction="test"))

    assert stderr not in str(caught.value)


def test_process_start_error_does_not_leak_sensitive_path(tmp_path: Path) -> None:
    runner = FakeProcessRunner(error=ProcessStartError("secret-path-error"))

    with pytest.raises(AIRuntimeUnexpectedError) as caught:
        runtime(tmp_path, runner).execute(AIRuntimeRequest(instruction="test"))

    assert "secret-path-error" not in str(caught.value)


def test_explicit_composition_registers_the_codex_runtime(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    config = CodexAIRuntimeConfig(workspace=tmp_path)

    registry = create_codex_ai_runtime_registry(
        config,
        process_runner=runner,
    )

    resolved = registry.get("codex")
    assert isinstance(resolved, CodexAIRuntime)
    assert resolved.identity.runtime_id == "codex"
    assert runner.calls == []
