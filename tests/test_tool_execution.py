from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from asep.agents import (
    AgentExecutionPolicy,
    AgentExecutionService,
    AgentExecutionValidationError,
    AgentId,
    AgentCapability,
)
from asep.agents.registry import InMemoryAgentRegistry
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEventType,
    TimelineRecorder,
)
from asep.tools import (
    InMemoryToolMetrics,
    InMemoryToolRegistry,
    ToolCapability,
    ToolCapabilityNotSupportedError,
    ToolContext,
    ToolError,
    ToolExecutionError,
    ToolExecutionPolicy,
    ToolExecutionService,
    ToolExecutionStatus,
    ToolId,
    ToolMetadata,
    ToolNotRegisteredError,
    ToolRequest,
    ToolResult,
    ToolRetryExhaustedError,
    ToolValidationError,
    WriteFileTool,
    ToolSecurityError,
    
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


class Clock:
    def __init__(self, *values: datetime) -> None:
        self._values = iter(values)

    def __call__(self) -> datetime:
        return next(self._values)


class FakeTool:
    def __init__(
        self,
        *,
        failures: int = 0,
        retryable: bool = False,
        status: ToolExecutionStatus = ToolExecutionStatus.SUCCEEDED,
    ) -> None:
        self.calls = 0
        self.failures = failures
        self.retryable = retryable
        self.status = status
        self.contexts: list[ToolContext] = []
        self._metadata = ToolMetadata(
            id=ToolId(value="fake"),
            name="Fake",
            description="Runtime fake.",
            version="1",
            author="tests",
            category="testing",
            capabilities=(ToolCapability(id="read"),),
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    def execute(
        self, request: ToolRequest, context: ToolContext
    ) -> ToolResult:
        self.calls += 1
        self.contexts.append(context)
        if self.calls <= self.failures:
            raise ToolExecutionError(
                "fake",
                error_type="TransientFailure",
                retryable=self.retryable,
            )
        error = (
            None
            if self.status is ToolExecutionStatus.SUCCEEDED
            else ToolError(code="failed", message="Structured failure.")
        )
        return ToolResult(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            status=self.status,
            output={"value": "ok"},
            duration_seconds=0,
            started_at=context.started_at,
            completed_at=context.started_at,
            attempts=context.attempt,
            error=error,
        )


def tool_request(tmp_path: Path, **changes) -> ToolRequest:
    values = {
        "execution_id": "tool-execution-1",
        "tool_id": ToolId(value="fake"),
        "capability": ToolCapability(id="read"),
        "workspace": tmp_path,
        "workflow_execution_id": "run-1",
        "correlation_id": "correlation-1",
        "metadata": {"safe": "visible"},
    }
    values.update(changes)
    return ToolRequest(**values)


def runtime(
    tool: FakeTool,
    *,
    policy: ToolExecutionPolicy | None = None,
    clock=None,
):
    registry = InMemoryToolRegistry()
    registry.register(tool)
    repository = InMemoryTimelineRepository()
    timeline = TimelineRecorder(repository)
    metrics = InMemoryToolMetrics()
    service = ToolExecutionService(
        registry,
        timeline=timeline,
        metrics=metrics,
        policy=policy,
        clock=clock,
    )
    return service, repository, metrics


def test_success_records_context_timeline_and_metrics(tmp_path: Path) -> None:
    tool = FakeTool()
    service, timeline, metrics = runtime(tool)

    result = service.execute(tool_request(tmp_path))

    assert result.status is ToolExecutionStatus.SUCCEEDED
    assert tool.contexts[0].workspace == tmp_path.resolve()
    assert [event.type for event in timeline.list_by_run("run-1")] == [
        TimelineEventType.TOOL_REQUESTED,
        TimelineEventType.TOOL_VALIDATED,
        TimelineEventType.TOOL_STARTED,
        TimelineEventType.TOOL_SUCCEEDED,
    ]
    snapshot = metrics.snapshot()
    assert snapshot.total == snapshot.succeeded == 1
    assert snapshot.by_tool == {"fake": 1}
    assert snapshot.by_capability == {"read": 1}


def test_missing_tool_is_rejected_fail_fast(tmp_path: Path) -> None:
    service, _, metrics = runtime(FakeTool())
    with pytest.raises(ToolNotRegisteredError):
        service.execute(
            tool_request(tmp_path, tool_id=ToolId(value="missing"))
        )
    assert metrics.snapshot().rejected == 1


def test_invalid_capability_is_rejected(tmp_path: Path) -> None:
    service, _, _ = runtime(FakeTool())
    with pytest.raises(ToolCapabilityNotSupportedError):
        service.execute(
            tool_request(
                tmp_path, capability=ToolCapability(id="write")
            )
        )


def test_invalid_workspace_is_rejected_as_result(tmp_path: Path) -> None:
    service, timeline, metrics = runtime(
        FakeTool(), policy=ToolExecutionPolicy(fail_fast=False)
    )
    result = service.execute(
        tool_request(tmp_path / "missing")
    )

    assert result.status is ToolExecutionStatus.REJECTED
    assert metrics.snapshot().rejected == 1
    assert timeline.list_by_run("run-1")[-1].type is (
        TimelineEventType.TOOL_REJECTED
    )


def test_structured_failure_is_returned(tmp_path: Path) -> None:
    service, timeline, metrics = runtime(
        FakeTool(status=ToolExecutionStatus.FAILED)
    )
    result = service.execute(tool_request(tmp_path))

    assert result.status is ToolExecutionStatus.FAILED
    assert result.error is not None
    assert metrics.snapshot().failed == 1
    assert timeline.list_by_run("run-1")[-1].type is (
        TimelineEventType.TOOL_FAILED
    )


def test_unexpected_failure_is_sanitized(tmp_path: Path) -> None:
    class BrokenTool(FakeTool):
        def execute(self, request, context):
            raise RuntimeError("authorization=do-not-expose")

    service, timeline, _ = runtime(
        BrokenTool(), policy=ToolExecutionPolicy(fail_fast=False)
    )
    result = service.execute(tool_request(tmp_path))
    rendered = repr(timeline.list_by_run("run-1"))

    assert result.error.metadata["error_type"] == "RuntimeError"
    assert "do-not-expose" not in rendered
    assert "do-not-expose" not in repr(result)


def test_retry_success_and_exhaustion(tmp_path: Path) -> None:
    policy = ToolExecutionPolicy(
        retry_enabled=True, max_attempts=2, fail_fast=False
    )
    service, _, metrics = runtime(
        FakeTool(failures=1, retryable=True), policy=policy
    )
    result = service.execute(tool_request(tmp_path))
    assert result.status is ToolExecutionStatus.SUCCEEDED
    assert result.attempts == 2
    assert metrics.snapshot().retries == 1

    failing, _, _ = runtime(
        FakeTool(failures=2, retryable=True),
        policy=ToolExecutionPolicy(
            retry_enabled=True, max_attempts=2, fail_fast=True
        ),
    )
    with pytest.raises(ToolRetryExhaustedError):
        failing.execute(
            tool_request(tmp_path, execution_id="exhausted")
        )


def test_timeout_is_deterministic(tmp_path: Path) -> None:
    service, timeline, metrics = runtime(
        FakeTool(),
        clock=Clock(NOW, NOW + timedelta(seconds=2)),
    )
    result = service.execute(
        tool_request(tmp_path, timeout_seconds=1)
    )

    assert result.status is ToolExecutionStatus.TIMED_OUT
    assert result.duration_seconds == 2
    assert metrics.snapshot().timed_out == 1
    assert timeline.list_by_run("run-1")[-1].type is (
        TimelineEventType.TOOL_TIMEOUT
    )


def test_completed_execution_is_idempotent(tmp_path: Path) -> None:
    tool = FakeTool()
    service, timeline, metrics = runtime(tool)
    request = tool_request(tmp_path)

    first = service.execute(request)
    second = service.execute(request)

    assert second is first
    assert tool.calls == 1
    assert len(timeline.list_by_run("run-1")) == 4
    assert metrics.snapshot().total == 1


def test_sensitive_metadata_is_filtered(tmp_path: Path) -> None:
    service, timeline, _ = runtime(FakeTool())
    result = service.execute(
        tool_request(
            tmp_path,
            metadata={
                "password": "password-value",
                "nested": {"api_key": "api-key-value", "safe": "kept"},
            },
        )
    )

    assert result.metadata == {"nested": {"safe": "kept"}}
    rendered = repr(timeline.list_by_run("run-1"))
    assert "password-value" not in rendered
    assert "api-key-value" not in rendered


def test_agent_runtime_delegates_tools_only_by_contract(tmp_path: Path) -> None:
    class ExecutorFake:
        def __init__(self) -> None:
            self.request = None

        def execute(self, request):
            self.request = request
            return FakeTool().execute(
                request,
                ToolContext(
                    execution_id=request.execution_id,
                    started_at=NOW,
                    workspace=request.workspace,
                ),
            )

    executor = ExecutorFake()
    service = AgentExecutionService(
        InMemoryAgentRegistry(),
        timeline=TimelineRecorder(InMemoryTimelineRepository()),
        policy=AgentExecutionPolicy(),
        tool_executor=executor,
    )
    request = tool_request(tmp_path)

    assert service.execute_tool(request).status is (
        ToolExecutionStatus.SUCCEEDED
    )
    assert executor.request is request

    unconfigured = AgentExecutionService(
        InMemoryAgentRegistry(),
        timeline=TimelineRecorder(InMemoryTimelineRepository()),
    )
    with pytest.raises(AgentExecutionValidationError):
        unconfigured.execute_tool(request)

def write_file_request(
    tmp_path: Path,
    *,
    path: str,
    content: str,
    overwrite: bool = False,
) -> ToolRequest:
    return ToolRequest(
        execution_id=f"write-{path}",
        tool_id=ToolId(value="write-file"),
        capability=ToolCapability(id="write_file"),
        workspace=tmp_path,
        payload={
            "path": path,
            "content": content,
            "overwrite": overwrite,
        },
        workflow_execution_id="run-write",
    )


def write_file_runtime() -> ToolExecutionService:
    registry = InMemoryToolRegistry()
    registry.register(WriteFileTool())

    return ToolExecutionService(
        registry,
        timeline=TimelineRecorder(
            InMemoryTimelineRepository(),
        ),
    )


def test_write_file_tool_creates_utf8_file(
    tmp_path: Path,
) -> None:
    service = write_file_runtime()

    result = service.execute(
        write_file_request(
            tmp_path,
            path="src/app.py",
            content='print("ASEP")\n',
        )
    )

    target = tmp_path / "src" / "app.py"

    assert result.status is ToolExecutionStatus.SUCCEEDED
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == 'print("ASEP")\n'
    assert result.output["path"] == "src/app.py"
    assert result.output["bytes_written"] == len(
        'print("ASEP")\n'.encode("utf-8")
    )
    assert result.output["overwritten"] is False


def test_write_file_tool_creates_parent_directories(
    tmp_path: Path,
) -> None:
    service = write_file_runtime()

    service.execute(
        write_file_request(
            tmp_path,
            path="src/domain/models/customer.py",
            content="class Customer:\n    pass\n",
        )
    )

    assert (
        tmp_path
        / "src"
        / "domain"
        / "models"
        / "customer.py"
    ).is_file()


def test_write_file_tool_refuses_overwrite_by_default(
    tmp_path: Path,
) -> None:
    target = tmp_path / "README.md"
    target.write_text("original", encoding="utf-8")

    service = write_file_runtime()

    with pytest.raises(ToolExecutionError):
        service.execute(
            write_file_request(
                tmp_path,
                path="README.md",
                content="novo conteúdo",
            )
        )

    assert target.read_text(encoding="utf-8") == "original"


def test_write_file_tool_allows_explicit_overwrite(
    tmp_path: Path,
) -> None:
    target = tmp_path / "README.md"
    target.write_text("original", encoding="utf-8")

    service = write_file_runtime()

    result = service.execute(
        write_file_request(
            tmp_path,
            path="README.md",
            content="atualizado",
            overwrite=True,
        )
    )

    assert result.status is ToolExecutionStatus.SUCCEEDED
    assert target.read_text(encoding="utf-8") == "atualizado"
    assert result.output["overwritten"] is True


def test_write_file_tool_rejects_path_outside_workspace(
    tmp_path: Path,
) -> None:
    service = write_file_runtime()

    with pytest.raises(ToolExecutionError) as captured:
        service.execute(
            write_file_request(
                tmp_path,
                path="../outside.py",
                content="malicious",
            )
        )
    assert "ToolSecurityError" in str(captured.value)
    assert not (tmp_path.parent / "outside.py").exists()