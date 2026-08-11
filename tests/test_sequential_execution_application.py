from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.application import (
    AuthorizedSequentialProject,
    SequentialExecution,
    SequentialExecutionNotFoundError,
    SequentialExecutionOwnershipError,
    SequentialProjectNotFoundError,
    SequentialExecutionSource,
    SequentialQualityGateQueryService,
)
from asep.errors import StatePersistenceError
from asep.execution.models import (
    ExecutionState,
    ExecutionStatus,
    GateDecision,
    StageState,
    StageStatus,
)
from asep.execution.state import StateManager
from asep.execution.state_source import ProjectScopedSequentialExecutionSource
from asep.quality_results import (
    InMemoryQualityGateResultRepository,
    StoredQualityGateResult,
)
from asep.project.sequential_resolver import ConfiguredSequentialProjectResolver

RUN_ID = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"
NOW = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


def resolver(
    project_id: str,
    project_path: Path,
) -> ConfiguredSequentialProjectResolver:
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "project.yaml").write_text(
        "\n".join((
            f"id: {project_id}", "name: Test", "version: 0.1.0",
            "status: active", "project_type: software",
            "workflow_id: software-project", "data_classification: internal",
        )),
        encoding="utf-8",
    )
    return ConfiguredSequentialProjectResolver((
        AuthorizedSequentialProject(project_id, project_path),
    ))


def state(status: ExecutionStatus = ExecutionStatus.RUNNING) -> ExecutionState:
    return ExecutionState(
        run_id=RUN_ID,
        project_id="sample",
        workflow_id="software-project",
        execution_status=status,
        current_stage="analysis",
        created_at=NOW,
        updated_at=NOW,
        resumed_at=None,
        stages=[
            StageState(
                id="analysis",
                agent_id="business-analyst",
                quality_gate_id="QG-ANALYSIS",
                status=StageStatus.RUNNING,
                attempts=2,
            )
        ],
    )


def persisted_source(
    tmp_path: Path,
    execution_state: ExecutionState | None = None,
) -> tuple[ProjectScopedSequentialExecutionSource, Path]:
    project_path = tmp_path / "project"
    state_path = project_path / ".asep" / "runs" / RUN_ID / "state.yaml"
    StateManager().save(execution_state or state(), state_path)
    return (
        ProjectScopedSequentialExecutionSource(
            resolver("sample", project_path), StateManager()
        ),
        state_path,
    )


@pytest.mark.parametrize("status", list(ExecutionStatus))
def test_projection_preserves_every_execution_status(
    tmp_path: Path,
    status: ExecutionStatus,
) -> None:
    source, _ = persisted_source(tmp_path, state(status))
    assert source.get("sample", RUN_ID).status is status


def test_projection_is_lossless_frozen_and_detached(tmp_path: Path) -> None:
    execution_state = state()
    source, _ = persisted_source(tmp_path, execution_state)
    projected = source.get("sample", RUN_ID)

    assert projected == SequentialExecution.from_state(execution_state)
    assert projected.execution_id == execution_state.run_id
    assert projected.stages[0].model_dump() == {
        "stage_id": "analysis",
        "agent_id": "business-analyst",
        "gate_id": "QG-ANALYSIS",
        "status": StageStatus.RUNNING,
        "attempts": 2,
    }
    execution_state.stages[0].attempts = 3
    assert projected.stages[0].attempts == 2
    with pytest.raises((FrozenInstanceError, ValueError)):
        projected.status = ExecutionStatus.FAILED  # type: ignore[misc]


def test_source_resolves_direct_path_without_glob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _ = persisted_source(tmp_path)

    def forbid_glob(*args, **kwargs):
        raise AssertionError("filesystem scan is forbidden")

    monkeypatch.setattr(Path, "glob", forbid_glob)
    monkeypatch.setattr(Path, "rglob", forbid_glob)
    assert source.get("sample", RUN_ID).execution_id == RUN_ID


def test_unknown_execution_has_typed_error(tmp_path: Path) -> None:
    source = ProjectScopedSequentialExecutionSource(
        resolver("sample", tmp_path / "project"), StateManager()
    )
    with pytest.raises(SequentialExecutionNotFoundError):
        source.get("sample", RUN_ID)


def test_unknown_project_and_state_project_mismatch_are_rejected(
    tmp_path: Path,
) -> None:
    source, state_path = persisted_source(tmp_path)
    with pytest.raises(SequentialProjectNotFoundError):
        source.get("other", RUN_ID)

    mismatched = state().model_copy(update={"project_id": "other"})
    StateManager().save(mismatched, state_path)
    with pytest.raises(SequentialExecutionOwnershipError):
        source.get("sample", RUN_ID)


def test_malformed_yaml_remains_explicit(tmp_path: Path) -> None:
    source, state_path = persisted_source(tmp_path)
    state_path.write_text("run_id: [invalid", encoding="utf-8")
    with pytest.raises(StatePersistenceError):
        source.get("sample", RUN_ID)


def test_persistence_survives_source_reconstruction(tmp_path: Path) -> None:
    _, state_path = persisted_source(tmp_path)
    reconstructed = ProjectScopedSequentialExecutionSource(
        resolver("sample", state_path.parents[3]), StateManager()
    )
    assert reconstructed.get("sample", RUN_ID).execution_id == RUN_ID


def test_query_returns_known_execution_with_zero_gates(tmp_path: Path) -> None:
    source, _ = persisted_source(tmp_path)
    service = SequentialQualityGateQueryService(
        source, InMemoryQualityGateResultRepository()
    )
    result = service.get("sample", RUN_ID)
    assert result.execution.execution_id == RUN_ID
    assert result.quality_gates == ()


def test_query_preserves_deterministic_gate_facts(tmp_path: Path) -> None:
    source, _ = persisted_source(tmp_path)
    gates = InMemoryQualityGateResultRepository()
    gates.record(StoredQualityGateResult(
        gate_id="QG-TEST", run_id=RUN_ID, stage_id="test",
        decision=GateDecision.BLOCKED, satisfied_criteria=("one",),
        unsatisfied_criteria=("two",), evaluated_at=NOW,
    ))
    gates.record(StoredQualityGateResult(
        gate_id="QG-ANALYSIS", run_id=RUN_ID, stage_id="analysis",
        decision=GateDecision.APPROVED_WITH_PENDING,
        satisfied_criteria=("three",), unsatisfied_criteria=(),
        evaluated_at=NOW,
    ))
    result = SequentialQualityGateQueryService(source, gates).get(
        "sample", RUN_ID
    )
    assert [item.gate_id for item in result.quality_gates] == [
        "QG-ANALYSIS", "QG-TEST"
    ]
    assert result.quality_gates[0].decision is GateDecision.APPROVED_WITH_PENDING
    assert result.quality_gates[0].satisfied_criteria == ("three",)
    assert set(type(result.quality_gates[0]).model_fields) == {
        "gate_id", "run_id", "stage_id", "decision",
        "satisfied_criteria", "unsatisfied_criteria", "evaluated_at",
    }


def test_orphan_gate_is_not_exposed_for_unknown_execution(tmp_path: Path) -> None:
    source = ProjectScopedSequentialExecutionSource(
        resolver("sample", tmp_path / "project"), StateManager()
    )
    gates = InMemoryQualityGateResultRepository()
    gates.record(StoredQualityGateResult(
        gate_id="QG-ANALYSIS", run_id=RUN_ID, stage_id="analysis",
        decision=GateDecision.APPROVED, evaluated_at=NOW,
    ))
    with pytest.raises(SequentialExecutionNotFoundError):
        SequentialQualityGateQueryService(source, gates).get("sample", RUN_ID)


def test_application_service_depends_on_protocols() -> None:
    assert isinstance(
        ProjectScopedSequentialExecutionSource(
            ConfiguredSequentialProjectResolver(), StateManager()
        ),
        SequentialExecutionSource,
    )
    source = inspect.getsource(SequentialQualityGateQueryService)
    assert "ProjectScopedSequentialExecutionSource" not in source
    assert "InMemoryQualityGateResultRepository" not in source
