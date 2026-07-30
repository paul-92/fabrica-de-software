from pathlib import Path

import pytest

import asep
from asep.pipeline import (
    GoalStatus,
    PipelineBuilder,
    PipelineComponentUnavailableError,
    PipelineComponents,
    PipelineValidator,
)
from asep.runtime.recovery import RecoveryPolicy, RetryPolicy
from asep.timeline import TimelineEventType
from asep.tools import (
    ListDirectoryTool,
    ReadFileTool,
    SearchFilesTool,
)
from asep.tools.builtin import ReadDocumentationTool
from asep.tools.exceptions import ToolExecutionError


def workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "docs" / "architecture").mkdir(parents=True)
    (tmp_path / "README.md").write_text(
        "# Sample\nA modular Python project.", encoding="utf-8"
    )
    (tmp_path / "src" / "app.py").write_text(
        "def main():\n    return 'ok'\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "architecture" / "ArchitectureMap.md").write_text(
        "# Architecture\nPipeline -> Runtime\n", encoding="utf-8"
    )
    return tmp_path


def test_complete_pipeline_uses_every_required_component(
    tmp_path: Path,
) -> None:
    engine = PipelineBuilder().build()

    result = engine.execute(
        "Analise este projeto e explique sua arquitetura.",
        workspace=workspace(tmp_path),
        metadata={"owner": "qa"},
    )

    assert result.status is GoalStatus.SUCCEEDED
    assert len(result.steps) == 4
    assert len(result.artifacts) == 4
    assert result.metrics["tools"]["total"] == 4
    assert result.metrics["agents"]["succeeded"] == 4
    assert result.metrics["memory"]["entries_total"] == 4
    assert result.metrics["planning"]["plans_created_total"] == 1
    assert result.metrics["coordination"]["coordinated_plans_total"] == 1
    assert result.metrics["recovery"]["executions_succeeded"] == 4
    event_types = {event.type for event in result.timeline}
    assert {
        TimelineEventType.RUN_STARTED,
        TimelineEventType.PLANNING_COMPLETED,
        TimelineEventType.COORDINATION_COMPLETED,
        TimelineEventType.EXECUTION_COMPLETED,
        TimelineEventType.TOOL_SUCCEEDED,
        TimelineEventType.MEMORY_SAVED,
        TimelineEventType.RUN_FINISHED,
    } <= event_types
    assert engine.pipeline.last_context is not None
    assert len(engine.pipeline.last_context.memory) == 4


def test_public_asep_execute_entrypoint(tmp_path: Path) -> None:
    result = asep.execute(
        goal="Resuma o diretório.",
        workspace=workspace(tmp_path),
    )

    assert result.status is GoalStatus.SUCCEEDED
    assert result.summary.startswith("Objetivo concluído")


def test_pipeline_validator_rejects_missing_components() -> None:
    components = PipelineComponents(
        workflow=None,  # type: ignore[arg-type]
        planner=None,  # type: ignore[arg-type]
        coordinator=None,  # type: ignore[arg-type]
        tools=None,  # type: ignore[arg-type]
        memory=None,  # type: ignore[arg-type]
        timeline=None,  # type: ignore[arg-type]
        metrics=None,
    )

    with pytest.raises(
        PipelineComponentUnavailableError, match="Workflow"
    ):
        PipelineValidator().validate_components(components)


def test_missing_tool_fails_without_skipping_pipeline_stage(
    tmp_path: Path,
) -> None:
    engine = PipelineBuilder(
        tools=(
            ListDirectoryTool(),
            SearchFilesTool(),
            ReadFileTool(),
        )
    ).build()

    result = engine.execute(
        "Analyze", workspace=workspace(tmp_path)
    )

    assert result.status is GoalStatus.FAILED
    assert "Capability indisponível" in result.summary


class FlakyListDirectoryTool(ListDirectoryTool):
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def execute(self, request, context):
        self.calls += 1
        if self.calls <= self.failures:
            raise ToolExecutionError(
                "list-directory",
                error_type="TemporaryFailure",
                retryable=True,
            )
        return super().execute(request, context)


def tool_set(directory_tool):
    return (
        directory_tool,
        SearchFilesTool(),
        ReadFileTool(),
        ReadDocumentationTool(),
    )


def test_recoverable_tool_error_is_retried_by_supervisor(
    tmp_path: Path,
) -> None:
    flaky = FlakyListDirectoryTool(failures=1)
    engine = PipelineBuilder(
        tools=tool_set(flaky),
        recovery_policy=RecoveryPolicy(
            retry=RetryPolicy(max_attempts=2)
        ),
    ).build()

    result = engine.execute(
        "Analyze", workspace=workspace(tmp_path)
    )

    assert result.status is GoalStatus.SUCCEEDED
    assert flaky.calls == 2
    assert result.metrics["recovery"]["retries_total"] == 1
    assert TimelineEventType.RETRY_COMPLETED in {
        event.type for event in result.timeline
    }


def test_permanent_tool_error_returns_failed_goal(
    tmp_path: Path,
) -> None:
    broken = FlakyListDirectoryTool(failures=10)
    engine = PipelineBuilder(
        tools=tool_set(broken),
        recovery_policy=RecoveryPolicy(
            retry=RetryPolicy(max_attempts=2)
        ),
    ).build()

    result = engine.execute(
        "Analyze", workspace=workspace(tmp_path)
    )

    assert result.status is GoalStatus.FAILED
    assert broken.calls == 2
    assert result.metrics["recovery"]["executions_failed"] == 1


def test_sensitive_metadata_is_not_returned_or_persisted(
    tmp_path: Path,
) -> None:
    engine = PipelineBuilder().build()

    result = engine.execute(
        "Analyze password=should-not-remain",
        workspace=workspace(tmp_path),
        metadata={"api_token": "secret-value", "owner": "qa"},
    )

    assert "api_token" not in result.metadata
    assert result.metadata["owner"] == "qa"
    memory_content = " ".join(
        item.content for item in engine.pipeline.last_context.memory
    )
    assert "should-not-remain" not in memory_content
    assert "[REDACTED]" in memory_content
