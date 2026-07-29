from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from asep.errors import (
    RunNotResumableError,
    StatePersistenceError,
    StateTransitionError,
)
from asep.execution.models import ExecutionStatus, RunContext, StageStatus
from asep.execution.state import StateManager
from asep.registry.loader import RegistryLoader
from asep.workflow.loader import WorkflowLoader


def workflow_from(sample_repository: Path):
    registry = RegistryLoader().load(sample_repository / "registry")
    return WorkflowLoader().load(registry.workflows["software-project"], registry)


def test_state_manager_creates_and_loads_atomic_state(
    sample_repository: Path,
) -> None:
    manager = StateManager()
    run_id = str(uuid4())
    path = sample_repository / "projects/sample/.asep/runs" / run_id / "state.yaml"

    created = manager.create(
        run_id,
        "sample",
        workflow_from(sample_repository),
        path,
        now=datetime(2026, 7, 28, tzinfo=UTC),
    )
    loaded = manager.load(path, expected_run_id=run_id)

    assert created == loaded
    assert not list(path.parent.glob("*.tmp"))


def test_state_manager_accepts_valid_and_rejects_invalid_transition(
    sample_repository: Path,
) -> None:
    manager = StateManager()
    run_id = str(uuid4())
    path = sample_repository / "state.yaml"
    state = manager.create(
        run_id, "sample", workflow_from(sample_repository), path
    )
    manager.transition_execution(
        state, ExecutionStatus.READY, "validado", "test"
    )

    with pytest.raises(StateTransitionError):
        manager.transition_execution(
            state, ExecutionStatus.COMPLETED, "fora de ordem", "test"
        )


def test_completed_run_cannot_resume(sample_repository: Path) -> None:
    manager = StateManager()
    run_id = str(uuid4())
    state = manager.create(
        run_id,
        "sample",
        workflow_from(sample_repository),
        sample_repository / "state.yaml",
    )
    manager.transition_execution(state, ExecutionStatus.READY, "ready", "test")
    manager.transition_execution(state, ExecutionStatus.RUNNING, "run", "test")
    manager.transition_stage(state, "intake", StageStatus.READY, "ready", "test")
    manager.transition_stage(state, "intake", StageStatus.RUNNING, "run", "test")
    manager.transition_stage(
        state, "intake", StageStatus.COMPLETED, "done", "test"
    )
    manager.transition_execution(
        state, ExecutionStatus.COMPLETED, "done", "test"
    )

    with pytest.raises(RunNotResumableError):
        manager.prepare_resume(state)


def test_run_context_requires_uuid4(sample_repository: Path) -> None:
    with pytest.raises(ValueError, match="UUID"):
        RunContext(
            run_id="invalid",
            project_id="sample",
            workflow_id="software-project",
            started_at=datetime.now(UTC),
            execution_status=ExecutionStatus.CREATED,
            project_path=sample_repository,
            state_path=sample_repository / "state.yaml",
            artifacts_path=sample_repository / "artifacts",
            logs_path=sample_repository / "logs.jsonl",
        )


def test_state_manager_refuses_overwrite(sample_repository: Path) -> None:
    manager = StateManager()
    path = sample_repository / "state.yaml"
    manager.create(
        str(uuid4()), "sample", workflow_from(sample_repository), path
    )

    with pytest.raises(StatePersistenceError, match="sobrescrita"):
        manager.create(
            str(uuid4()), "sample", workflow_from(sample_repository), path
        )


def test_state_manager_rejects_mismatched_run_id_on_load(
    sample_repository: Path,
) -> None:
    manager = StateManager()
    path = sample_repository / "state.yaml"
    manager.create(
        str(uuid4()), "sample", workflow_from(sample_repository), path
    )

    with pytest.raises(StatePersistenceError, match="diverge"):
        manager.load(path, expected_run_id=str(uuid4()))


def test_state_manager_rejects_unknown_stage(sample_repository: Path) -> None:
    manager = StateManager()
    state = manager.create(
        str(uuid4()),
        "sample",
        workflow_from(sample_repository),
        sample_repository / "state.yaml",
    )

    with pytest.raises(StateTransitionError, match="não existe"):
        manager.stage(state, "unknown")
