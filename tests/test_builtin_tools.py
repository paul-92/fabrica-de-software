from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.providers.process import (
    ProcessResult,
    ProcessStartError,
    ProcessTimeoutError,
)
from asep.tools import (
    ListDirectoryTool,
    ReadDocumentationTool,
    ReadFileTool,
    RunTestsTool,
    SearchFilesTool,
    ToolCapability,
    ToolContext,
    ToolExecutionStatus,
    ToolId,
    ToolRequest,
    ToolSecurityError,
    ToolExecutionError,
    ToolTimeoutError,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def call(tool, workspace: Path, payload: dict, capability: str):
    request = ToolRequest(
        execution_id="builtin-1",
        tool_id=tool.metadata.id,
        capability=ToolCapability(id=capability),
        workspace=workspace,
        payload=payload,
    )
    context = ToolContext(
        execution_id=request.execution_id,
        started_at=NOW,
        workspace=workspace.resolve(),
    )
    return tool.execute(request, context)


def test_read_file_reads_utf8(tmp_path: Path) -> None:
    (tmp_path / "hello.txt").write_text("olá", encoding="utf-8")

    result = call(
        ReadFileTool(), tmp_path, {"path": "hello.txt"}, "read_file"
    )

    assert result.output == {"path": "hello.txt", "content": "olá"}


def test_read_file_rejects_directory_and_invalid_utf8(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()
    with pytest.raises(ToolExecutionError):
        call(
            ReadFileTool(), tmp_path, {"path": "folder"}, "read_file"
        )

    (tmp_path / "binary.bin").write_bytes(b"\xff")
    with pytest.raises(ToolExecutionError):
        call(
            ReadFileTool(), tmp_path, {"path": "binary.bin"}, "read_file"
        )


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "../../outside.txt",
        ".git/config",
        ".env",
        ".env.local",
    ],
)
def test_read_file_blocks_unsafe_paths(tmp_path: Path, path: str) -> None:
    with pytest.raises(ToolSecurityError):
        call(ReadFileTool(), tmp_path, {"path": path}, "read_file")


def test_read_file_blocks_absolute_path(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("value", encoding="utf-8")
    with pytest.raises(ToolSecurityError):
        call(
            ReadFileTool(),
            tmp_path,
            {"path": str(target.resolve())},
            "read_file",
        )


def test_external_symlink_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        original_resolve = Path.resolve

        def resolve(candidate: Path, *args, **kwargs) -> Path:
            if candidate == link:
                return original_resolve(outside, *args, **kwargs)
            return original_resolve(candidate, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", resolve)

    with pytest.raises(ToolSecurityError):
        call(ReadFileTool(), tmp_path, {"path": "link.txt"}, "read_file")


def test_list_directory_is_sorted_and_hides_critical_entries(
    tmp_path: Path,
) -> None:
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a").mkdir()
    (tmp_path / ".git").mkdir()

    result = call(ListDirectoryTool(), tmp_path, {}, "directory")

    assert result.output["entries"] == (
        {"path": "a", "type": "directory"},
        {"path": "b.txt", "type": "file"},
    )

    with pytest.raises(ToolExecutionError):
        call(
            ListDirectoryTool(),
            tmp_path,
            {"path": "b.txt"},
            "directory",
        )


def test_search_files_by_name_extension_and_text(tmp_path: Path) -> None:
    (tmp_path / "alpha.md").write_text("needle", encoding="utf-8")
    (tmp_path / "beta.md").write_text("other", encoding="utf-8")
    (tmp_path / "alpha.txt").write_text("needle", encoding="utf-8")

    result = call(
        SearchFilesTool(),
        tmp_path,
        {"name": "alpha", "extension": "md", "text": "needle"},
        "search",
    )

    assert result.output["matches"] == ("alpha.md",)

    with pytest.raises(ToolExecutionError):
        call(SearchFilesTool(), tmp_path, {}, "search")
    with pytest.raises(ToolExecutionError):
        call(
            SearchFilesTool(),
            tmp_path,
            {"path": "alpha.md", "name": "alpha"},
            "search",
        )


def test_documentation_tool_is_confined_to_docs(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("guide", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")

    result = call(
        ReadDocumentationTool(),
        tmp_path,
        {"path": "guide.md"},
        "documentation",
    )
    assert result.output["path"] == "docs/guide.md"

    with pytest.raises(ToolSecurityError):
        call(
            ReadDocumentationTool(),
            tmp_path,
            {"path": "../secret.txt"},
            "documentation",
        )

    with pytest.raises(ToolExecutionError):
        call(
            ReadDocumentationTool(),
            tmp_path,
            {"path": "."},
            "documentation",
        )
    (tmp_path / "docs" / "binary.md").write_bytes(b"\xff")
    with pytest.raises(ToolExecutionError):
        call(
            ReadDocumentationTool(),
            tmp_path,
            {"path": "binary.md"},
            "documentation",
        )


class FakeRunner:
    def __init__(
        self, *, exit_code: int = 0, timeout: bool = False
    ) -> None:
        self.exit_code = exit_code
        self.timeout = timeout
        self.calls = []
        self.start_error = False

    def is_available(self, executable: str) -> bool:
        return True

    def run(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if self.timeout:
            raise ProcessTimeoutError(kwargs["timeout"])
        if self.start_error:
            raise ProcessStartError("OSError")
        return ProcessResult(
            command=command,
            exit_code=self.exit_code,
            stdout="tests output",
            stderr="",
        )


def test_run_tests_uses_fixed_command_and_workspace(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    runner = FakeRunner()
    tool = RunTestsTool(runner, executable="python-safe")

    result = call(
        tool, tmp_path, {"paths": ["tests"]}, "test"
    )

    command, kwargs = runner.calls[0]
    assert command == ("python-safe", "-m", "pytest", "tests")
    assert kwargs["working_directory"] == tmp_path.resolve()
    assert result.status is ToolExecutionStatus.SUCCEEDED


def test_run_tests_reports_failure_and_timeout(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    failed = call(
        RunTestsTool(FakeRunner(exit_code=1), executable="python-safe"),
        tmp_path,
        {"paths": ["tests"]},
        "test",
    )
    assert failed.status is ToolExecutionStatus.FAILED
    assert failed.error.code == "tests_failed"

    with pytest.raises(ToolTimeoutError):
        call(
            RunTestsTool(FakeRunner(timeout=True), executable="python-safe"),
            tmp_path,
            {"paths": ["tests"]},
            "test",
        )


def test_run_tests_rejects_arbitrary_arguments(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    runner = FakeRunner()
    tool = RunTestsTool(runner, executable="python-safe")

    with pytest.raises(ToolSecurityError):
        call(
            tool,
            tmp_path,
            {"paths": ["../../outside"]},
            "test",
        )
    assert runner.calls == []


def test_run_tests_reports_missing_payload_path_explicitly(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()

    with pytest.raises(ToolExecutionError) as captured:
        call(
            RunTestsTool(runner, executable="python-safe"),
            tmp_path,
            {"paths": ["tests"]},
            "test",
        )

    assert captured.value.error_type == "InvalidTestPath"
    assert "payload.paths[0]='tests'" in str(captured.value)
    assert runner.calls == []


def test_run_tests_rejects_absolute_external_path(tmp_path: Path) -> None:
    runner = FakeRunner()

    with pytest.raises(ToolSecurityError):
        call(
            RunTestsTool(runner, executable="python-safe"),
            tmp_path,
            {"paths": [str(tmp_path.parent)]},
            "test",
        )

    assert runner.calls == []


def test_run_tests_rejects_invalid_payload_and_maps_process_error(
    tmp_path: Path,
) -> None:
    (tmp_path / "tests").mkdir()
    tool = RunTestsTool(FakeRunner(), executable="python-safe")
    for paths in ([], "tests", [1]):
        with pytest.raises(ToolExecutionError):
            call(tool, tmp_path, {"paths": paths}, "test")

    runner = FakeRunner()
    runner.start_error = True
    with pytest.raises(ToolExecutionError):
        call(
            RunTestsTool(runner, executable="python-safe"),
            tmp_path,
            {"paths": ["tests"]},
            "test",
        )
