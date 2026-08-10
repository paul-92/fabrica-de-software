from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from asep.application import (
    SessionMemoryExtractor,
    SessionMemoryPolicy,
    SessionMemorySelector,
    serialize_session_memory_context,
)
from asep.errors import ProjectHistoryConflictError
from asep.projects import (
    InMemorySessionMemoryRepository,
    ProjectExecution,
    ProjectExecutionStatus,
    SQLiteSessionMemoryRepository,
    SQLiteProjectRepository,
    SQLiteProjectSessionRepository,
    ProjectSession,
    SessionMemoryEntry,
    SessionMemoryKind,
)
from asep.workspace_changes import WorkspaceChange, WorkspaceChangeType
from asep.projects.models import WorkspaceProject


NOW = datetime(2026, 8, 10, tzinfo=UTC)


def entry(memory_id: str, *, session: str = "s-1", project: str = "p-1", content: str = "Use PostgreSQL", offset: int = 0) -> SessionMemoryEntry:
    return SessionMemoryEntry(memory_id=memory_id, session_id=session, project_id=project, kind=SessionMemoryKind.CONSTRAINT, content=content, created_at=NOW + timedelta(seconds=offset))


def test_model_is_strict_immutable_and_requires_aware_timestamp() -> None:
    item = entry("m-1")
    assert item.is_manual
    with pytest.raises(ValidationError):
        item.content = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        SessionMemoryEntry(memory_id="m", session_id="s", project_id="p", kind="fact", content="x", created_at=datetime(2026, 1, 1), unknown=True)


@pytest.mark.parametrize("repository_factory", [InMemorySessionMemoryRepository])
def test_repository_add_get_order_and_session_isolation(repository_factory) -> None:
    repository = repository_factory()
    repository.add(entry("m-1")); repository.add(entry("m-2", offset=1)); repository.add(entry("m-3", session="s-2"))
    assert repository.get("m-1") == entry("m-1")
    assert [item.memory_id for item in repository.list_by_session("s-1")] == ["m-2", "m-1"]
    with pytest.raises(ProjectHistoryConflictError): repository.add(entry("m-1"))


def test_sqlite_survives_restart_and_deduplicates_normalized_content(tmp_path) -> None:
    path = tmp_path / "asep.db"
    SQLiteProjectRepository(path).save(WorkspaceProject(project_id="p-1", name="P", workspace_path=tmp_path, created_at=NOW, updated_at=NOW))
    SQLiteProjectSessionRepository(path).create(ProjectSession(session_id="s-1", project_id="p-1", title="S", created_at=NOW, updated_at=NOW))
    SQLiteSessionMemoryRepository(path).add(entry("m-1"))
    restarted = SQLiteSessionMemoryRepository(path)
    assert restarted.get("m-1").content == "Use PostgreSQL"
    with pytest.raises(ProjectHistoryConflictError):
        restarted.add(entry("m-2", content=" use   postgresql "))


def test_selector_is_recent_bounded_deterministic_and_reports_truncation() -> None:
    entries = tuple(entry(f"m-{index}", content="á" * 80, offset=index) for index in range(3, 0, -1))
    selector = SessionMemorySelector(SessionMemoryPolicy(max_memory_entries=2, max_memory_content_chars=50, max_memory_context_chars=500))
    first = selector.select(entries)
    assert [item.memory_id for item in first.entries] == ["m-2", "m-3"]
    assert first.truncated
    assert serialize_session_memory_context(first) == serialize_session_memory_context(selector.select(entries))


def test_extractor_only_uses_created_changes_from_success() -> None:
    execution = ProjectExecution(execution_id="e", session_id="s", project_id="p", runtime_id="codex", instruction="infer nothing", execution_mode="workspace_write", status=ProjectExecutionStatus.SUCCEEDED, changes=(WorkspaceChange(path="z.py", change_type=WorkspaceChangeType.MODIFIED), WorkspaceChange(path="a.py", change_type=WorkspaceChangeType.CREATED)), created_at=NOW, completed_at=NOW)
    assert [draft.content for draft in SessionMemoryExtractor().extract(execution)] == ["Created a.py"]
    failed = execution.model_copy(update={"status": ProjectExecutionStatus.FAILED, "error_code": "FAILED"})
    assert SessionMemoryExtractor().extract(failed) == ()
