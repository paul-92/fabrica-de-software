from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import json
import sqlite3
from pydantic import ValidationError

from asep.ai_runtime import AIRuntimeExecutionMode, AIRuntimeUsage
from asep.errors import ProjectExecutionNotFoundError, ProjectHistoryConflictError, ProjectSessionNotFoundError
from asep.projects import (
    InMemoryProjectExecutionRepository, InMemoryProjectSessionRepository,
    ProjectExecution, ProjectExecutionStatus, ProjectSession,
    ProjectOperationalPlan, ProjectOperationalPlanOperation,
    ProjectOperationalPlanStep,
    SQLiteProjectExecutionRepository, SQLiteProjectRepository, SQLiteProjectSessionRepository,
    WorkspaceProject,
)
from asep.workspace_changes import WorkspaceChange, WorkspaceChangeType

NOW = datetime(2026, 8, 7, tzinfo=UTC)


def session(identifier: str = "s-1", project: str = "p-1", offset: int = 0) -> ProjectSession:
    moment = NOW + timedelta(seconds=offset)
    return ProjectSession(session_id=identifier, project_id=project, title="Work", created_at=moment, updated_at=moment)


def execution(identifier: str = "e-1", session_id: str = "s-1", project: str = "p-1", offset: int = 0) -> ProjectExecution:
    return ProjectExecution(
        execution_id=identifier, session_id=session_id, project_id=project,
        runtime_id="codex", instruction="Inspect", execution_mode=AIRuntimeExecutionMode.READ_ONLY,
        status=ProjectExecutionStatus.SUCCEEDED, output="done", model="model",
        usage=AIRuntimeUsage(input_units=2, output_units=1, total_units=3),
        changes=(WorkspaceChange(path="a.txt", change_type=WorkspaceChangeType.CREATED, size_after=1),),
        created_at=NOW + timedelta(seconds=offset), completed_at=NOW + timedelta(seconds=offset + 1),
    )


def test_models_are_strict_immutable_and_validate_time_and_status() -> None:
    item = session()
    with pytest.raises(ValidationError):
        item.title = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ProjectSession(session_id=" ", project_id="p", title="x", created_at=NOW, updated_at=NOW)
    with pytest.raises(ValidationError):
        ProjectExecution(execution_id="e", session_id="s", project_id="p", runtime_id="r",
                         instruction="x", execution_mode=AIRuntimeExecutionMode.READ_ONLY,
                         status=ProjectExecutionStatus.SUCCEEDED, created_at=NOW)


def test_in_memory_repositories_are_ordered_isolated_and_explicit() -> None:
    sessions = InMemoryProjectSessionRepository(); executions = InMemoryProjectExecutionRepository()
    sessions.create(session("s-old", offset=0)); sessions.create(session("s-new", offset=2)); sessions.create(session("foreign", "p-2", 3))
    assert [item.session_id for item in sessions.list_by_project("p-1")] == ["s-new", "s-old"]
    with pytest.raises(ProjectHistoryConflictError): sessions.create(session("s-old"))
    with pytest.raises(ProjectSessionNotFoundError): sessions.get("missing")
    executions.create(execution("e-old", "s-old", offset=0)); executions.create(execution("e-new", "s-new", offset=2)); executions.create(execution("e-other", "foreign", "p-2", 3))
    assert [item.execution_id for item in executions.list_by_project("p-1")] == ["e-new", "e-old"]
    assert [item.execution_id for item in executions.list_by_session("s-old")] == ["e-old"]
    with pytest.raises(ProjectExecutionNotFoundError): executions.get("missing")


def test_sqlite_history_persists_between_instances(tmp_path: Path) -> None:
    database = tmp_path / "asep.db"
    SQLiteProjectRepository(database).save(WorkspaceProject(project_id="p-1", name="P", workspace_path=tmp_path, created_at=NOW, updated_at=NOW))
    SQLiteProjectSessionRepository(database).create(session())
    observed = execution().model_copy(update={
        "context_entry_count": 5,
        "context_truncated": True,
        "context_char_count": 17_432,
        "context_omitted_execution_count": 9,
    })
    SQLiteProjectExecutionRepository(database).create(observed)
    assert SQLiteProjectSessionRepository(database).get("s-1") == session()
    restored = SQLiteProjectExecutionRepository(database).get("e-1")
    assert restored == observed
    assert restored.usage.total_units == 3
    assert restored.changes[0].path == "a.txt"
    assert restored.context_entry_count == 5
    assert restored.context_truncated is True
    assert restored.context_char_count == 17_432
    assert restored.context_omitted_execution_count == 9


def test_sqlite_loads_pre_23_8_execution_payload_with_safe_context_defaults(tmp_path: Path) -> None:
    database = tmp_path / "asep.db"
    SQLiteProjectRepository(database).save(WorkspaceProject(project_id="p-1", name="P", workspace_path=tmp_path, created_at=NOW, updated_at=NOW))
    SQLiteProjectSessionRepository(database).create(session())
    legacy_payload = execution().model_dump(mode="json")
    legacy_payload.pop("context_entry_count")
    legacy_payload.pop("context_truncated")
    legacy_payload.pop("context_char_count")
    legacy_payload.pop("context_omitted_execution_count")
    legacy_payload.pop("step_results")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO project_executions (id, session_id, project_id, status, created_at, payload) VALUES (?, ?, ?, ?, ?, ?)",
            ("legacy", "s-1", "p-1", "succeeded", NOW.isoformat(), json.dumps({**legacy_payload, "execution_id": "legacy"})),
        )
    restored = SQLiteProjectExecutionRepository(database).get("legacy")
    assert restored.context_entry_count == 0
    assert restored.context_truncated is False
    assert restored.context_char_count == 0
    assert restored.context_omitted_execution_count == 0
    assert restored.step_results == ()


def test_sqlite_reconstructs_structured_plan_and_historical_step_defaults(
    tmp_path: Path,
) -> None:
    database = tmp_path / "asep.db"
    SQLiteProjectRepository(database).save(WorkspaceProject(
        project_id="p-1", name="P", workspace_path=tmp_path,
        created_at=NOW, updated_at=NOW,
    ))
    SQLiteProjectSessionRepository(database).create(session())
    structured = execution().model_copy(update={
        "operational_plan": ProjectOperationalPlan(
            execution_id="e-1",
            steps=(ProjectOperationalPlanStep(
                step_id="validate",
                operation=ProjectOperationalPlanOperation.VALIDATE,
                description="Validate",
                dependencies=("inspect",),
                target_hints=("tests",),
                validation_hints=("pytest",),
            ), ProjectOperationalPlanStep(
                step_id="inspect",
                operation=ProjectOperationalPlanOperation.INSPECT,
                description="Inspect",
            )),
            created_at=NOW,
        )
    })
    SQLiteProjectExecutionRepository(database).create(structured)
    restored = SQLiteProjectExecutionRepository(database).get("e-1")
    assert restored.operational_plan == structured.operational_plan

    payload = structured.model_dump(mode="json")
    legacy_step = payload["operational_plan"]["steps"][1]
    legacy_step.pop("dependencies")
    legacy_step.pop("target_hints")
    legacy_step.pop("validation_hints")
    payload["operational_plan"].pop("source")
    payload.pop("validation_strategy")
    payload.pop("failure_analyses")
    payload["execution_id"] = "legacy-plan"
    payload["operational_plan"]["execution_id"] = "legacy-plan"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO project_executions (id, session_id, project_id, status, created_at, payload) VALUES (?, ?, ?, ?, ?, ?)",
            ("legacy-plan", "s-1", "p-1", "succeeded", NOW.isoformat(), json.dumps(payload)),
        )
    legacy = SQLiteProjectExecutionRepository(database).get("legacy-plan")
    assert legacy.operational_plan.steps[1].dependencies == ()
    assert legacy.operational_plan.steps[1].target_hints == ()
    assert legacy.operational_plan.steps[1].validation_hints == ()
    assert legacy.operational_plan.source.value == "deterministic"
    assert legacy.validation_strategy is None
    assert legacy.failure_analyses == ()
