from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.providers.process import ProcessResult, ProcessRunner
from asep.tools import (
    NpmScriptValidationTool,
    ToolCapability,
    ToolContext,
    ToolExecutionError,
    ToolId,
    ToolRequest,
    ToolSecurityError,
    node_validation_tools,
    resolve_npm_executable,
)


class RecordingRunner:
    def __init__(self, *, exit_code: int = 0) -> None:
        self.exit_code = exit_code
        self.calls = []

    def is_available(self, executable: str) -> bool:
        return True

    def run(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return ProcessResult(
            command=command,
            exit_code=self.exit_code,
            stdout="ok" if self.exit_code == 0 else "failed",
            stderr="",
        )


def execute_tool(tool, workspace: Path, package_root: object = "."):
    now = datetime.now(UTC)
    request = ToolRequest(
        execution_id="node-validation-1",
        tool_id=tool.metadata.id,
        capability=tool.metadata.capabilities[0],
        workspace=workspace,
        payload={"package_root": package_root},
    )
    context = ToolContext(
        execution_id=request.execution_id,
        started_at=now,
        workspace=workspace,
    )
    return tool.execute(request, context)


@pytest.mark.parametrize(
    ("tool_id", "script"),
    (
        ("typecheck", "typecheck"),
        ("vitest", "test"),
        ("eslint", "lint"),
        ("next-build", "build"),
    ),
)
def test_node_validator_uses_only_its_fixed_script(
    tmp_path: Path, tool_id: str, script: str,
) -> None:
    package = tmp_path / "web"
    package.mkdir()
    (package / "package.json").write_text("{}", encoding="utf-8")
    runner = RecordingRunner()
    tool = NpmScriptValidationTool(
        tool_id, "validation", script, runner=runner, executable="npm-fixed",
    )

    result = execute_tool(tool, tmp_path, "web")

    command, options = runner.calls[0]
    assert command == ("npm-fixed", "run", script)
    assert options["working_directory"] == package
    assert options["environment"] == {}
    assert result.output["command"] == ("npm-fixed", "run", script)


def test_node_validator_rejects_command_shaped_payload(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    tool = NpmScriptValidationTool(
        "eslint", "lint", "lint", runner=RecordingRunner(), executable="npm",
    )
    now = datetime.now(UTC)
    request = ToolRequest(
        execution_id="node-validation-1",
        tool_id=ToolId(value="eslint"),
        capability=ToolCapability(id="lint"),
        workspace=tmp_path,
        payload={"package_root": ".", "args": ["--fix"]},
    )
    context = ToolContext(
        execution_id=request.execution_id, started_at=now, workspace=tmp_path,
    )

    with pytest.raises(ToolExecutionError, match="eslint"):
        tool.execute(request, context)


@pytest.mark.parametrize("package_root", ("../outside", "C:/outside"))
def test_node_validator_rejects_unsafe_package_root(
    tmp_path: Path, package_root: str,
) -> None:
    tool = NpmScriptValidationTool(
        "typecheck", "typecheck", "typecheck",
        runner=RecordingRunner(), executable="npm",
    )
    with pytest.raises((ToolSecurityError, ToolExecutionError)):
        execute_tool(tool, tmp_path, package_root)


def test_node_validator_requires_package_manifest(tmp_path: Path) -> None:
    tool = NpmScriptValidationTool(
        "vitest", "test", "test", runner=RecordingRunner(), executable="npm",
    )
    with pytest.raises(ToolExecutionError, match="vitest"):
        execute_tool(tool, tmp_path)


@pytest.mark.parametrize(
    ("platform_name", "expected"), (("nt", "npm.cmd"), ("posix", "npm")),
)
def test_npm_resolution_is_platform_specific(
    platform_name: str, expected: str,
) -> None:
    observed = []

    def resolver(executable: str) -> str:
        observed.append(executable)
        return f"/resolved/{executable}"

    assert resolve_npm_executable(
        platform_name=platform_name, resolver=resolver,
    ) == f"/resolved/{expected}"
    assert observed == [expected]


def test_all_node_validation_tools_are_registered_by_factory() -> None:
    assert {
        tool.metadata.id.value: tool.metadata.capabilities[0].id
        for tool in node_validation_tools()
    } == {
        "typecheck": "typecheck",
        "vitest": "frontend_test",
        "eslint": "lint",
        "next-build": "build",
    }


def test_process_runner_never_uses_a_shell(monkeypatch, tmp_path: Path) -> None:
    observed = {}

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def run(command, **kwargs):
        observed.update(kwargs)
        return Completed()

    monkeypatch.setattr("asep.providers.process.subprocess.run", run)
    ProcessRunner().run(
        ("npm", "run", "test"),
        input_text="",
        timeout=1,
        working_directory=tmp_path,
        environment={},
        encoding="utf-8",
    )

    assert observed["shell"] is False


def test_process_runner_does_not_copy_backend_secrets(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ASEP_SESSION_SECRET", "session-secret")
    monkeypatch.setenv("DATABASE_URL", "database-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "provider-secret")
    observed = {}

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def run(command, **kwargs):
        observed.update(kwargs)
        return Completed()

    monkeypatch.setattr("asep.providers.process.subprocess.run", run)
    ProcessRunner().run(("python", "-V"), input_text="", timeout=1,
                        working_directory=tmp_path, environment={}, encoding="utf-8")
    assert "PATH" in observed["env"]
    assert not {"ASEP_SESSION_SECRET", "DATABASE_URL", "OPENAI_API_KEY"} & set(observed["env"])
