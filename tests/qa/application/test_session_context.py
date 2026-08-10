from datetime import UTC, datetime, timedelta

from asep.ai_runtime import AIRuntimeExecutionMode
from asep.application import SessionContextBuilder, SessionContextPolicy
from asep.projects import InMemoryProjectExecutionRepository, ProjectExecution, ProjectExecutionStatus
from asep.workspace_changes import WorkspaceChange, WorkspaceChangeType
import pytest
from pydantic import ValidationError

NOW = datetime(2026, 8, 10, tzinfo=UTC)


def execution(identifier: str, instruction: str = "instruction", output: str | None = "summary", *,
              project_id: str = "project-1", session_id: str = "session-1",
              status: ProjectExecutionStatus = ProjectExecutionStatus.SUCCEEDED,
              offset: int = 0, changes: tuple[WorkspaceChange, ...] = ()) -> ProjectExecution:
    terminal = status in {ProjectExecutionStatus.SUCCEEDED, ProjectExecutionStatus.FAILED}
    return ProjectExecution(
        execution_id=identifier, session_id=session_id, project_id=project_id,
        runtime_id="codex", instruction=instruction,
        execution_mode=AIRuntimeExecutionMode.READ_ONLY, status=status, output=output,
        error_code="SAFE_FAILURE" if status is ProjectExecutionStatus.FAILED else None,
        created_at=NOW + timedelta(seconds=offset),
        completed_at=NOW + timedelta(seconds=offset + 1) if terminal else None,
        changes=changes,
    )


def build(*items: ProjectExecution, policy: SessionContextPolicy | None = None):
    repository = InMemoryProjectExecutionRepository()
    for item in items:
        repository.create(item)
    return SessionContextBuilder(repository, policy).build("project-1", "session-1")


def test_zero_executions_is_empty_and_not_truncated() -> None:
    context = build()
    assert context.entries == ()
    assert context.truncated is False


def test_context_models_and_policy_are_strict_and_immutable() -> None:
    context = build(execution("one"))
    with pytest.raises(ValidationError):
        context.truncated = True  # type: ignore[misc]
    with pytest.raises(ValidationError):
        SessionContextPolicy(max_entries=8, frontend_override=99)  # type: ignore[call-arg]


def test_recent_entries_are_presented_chronologically() -> None:
    context = build(
        execution("old", "first", "one", offset=1),
        execution("middle", "second", "two", offset=2),
        execution("new", "third", "three", offset=3),
        policy=SessionContextPolicy(max_entries=2),
    )
    assert [entry.execution_id for entry in context.entries] == ["middle", "new"]
    assert context.truncated is True


def test_completed_statuses_are_projected_and_non_terminal_statuses_are_ignored() -> None:
    change = WorkspaceChange(path="src/customer.py", change_type=WorkspaceChangeType.MODIFIED,
                             size_before=1, size_after=2)
    context = build(
        execution("success", offset=1),
        execution("failed", output=None, status=ProjectExecutionStatus.FAILED,
                  changes=(change,), offset=2),
        execution("pending", output=None, status=ProjectExecutionStatus.PENDING, offset=3),
        execution("running", output=None, status=ProjectExecutionStatus.RUNNING, offset=4),
    )
    assert [entry.status for entry in context.entries] == [
        ProjectExecutionStatus.SUCCEEDED, ProjectExecutionStatus.FAILED,
    ]
    failed = context.entries[1]
    assert failed.summary is None
    assert failed.error_code == "SAFE_FAILURE"
    assert failed.changes[0].model_dump(mode="json") == {
        "path": "src/customer.py", "change_type": "modified",
    }


def test_project_and_session_isolation_is_explicit() -> None:
    context = build(
        execution("same", offset=1),
        execution("other-session", session_id="session-2", offset=2),
        execution("other-project", project_id="project-2", offset=3),
    )
    assert [entry.execution_id for entry in context.entries] == ["same"]


def test_individual_and_total_limits_report_truncation_and_favor_recency() -> None:
    context = build(
        execution("old", "old instruction", "old summary", offset=1),
        execution("new", "new instruction", "new summary", offset=2),
        policy=SessionContextPolicy(max_instruction_chars_per_entry=3,
                                    max_summary_chars_per_entry=4, max_total_chars=7),
    )
    assert len(context.entries) == 1
    entry = context.entries[0]
    assert (entry.execution_id, entry.instruction, entry.summary) == ("new", "new", "new ")
    assert entry.instruction_truncated and entry.summary_truncated and context.truncated


def test_unicode_multiline_is_preserved_and_invalid_surrogate_is_replaced() -> None:
    context = build(execution("unicode", "Olá " + chr(0xD800) + "\nlinha", "Ação " + chr(0xDCFF)))
    entry = context.entries[0]
    assert entry.instruction == "Olá ?\nlinha"
    assert entry.summary == "Ação ?"
    entry.model_dump_json()


def test_same_history_and_policy_are_deterministic() -> None:
    items = (execution("one", offset=1), execution("two", offset=2))
    assert build(*items).model_dump_json() == build(*items).model_dump_json()


def test_change_count_and_path_limits_are_explicit() -> None:
    changes = (
        WorkspaceChange(path="a" * 10, change_type=WorkspaceChangeType.CREATED),
        WorkspaceChange(path="second", change_type=WorkspaceChangeType.DELETED),
    )
    context = build(execution("changed", changes=changes), policy=SessionContextPolicy(
        max_changes_per_entry=1, max_change_path_chars=3,
    ))
    assert context.entries[0].changes[0].path == "aaa"
    assert context.entries[0].changes_truncated and context.truncated
