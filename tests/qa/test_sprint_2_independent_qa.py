"""Testes independentes de QA da Sprint 2.

Estes testes documentam tanto garantias quanto comportamentos inseguros observados.
Eles não alteram código de produção.
"""

from __future__ import annotations

import logging
import multiprocessing
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from asep.artifacts.manager import ArtifactManager
from asep.errors import (
    AgentExecutionError,
    ArtifactError,
    RunNotResumableError,
    StatePersistenceError,
    StateTransitionError,
)
from asep.execution.engine import SequentialWorkflowEngine
from asep.execution.models import (
    AgentContext,
    ArtifactDraft,
    ExecutionStatus,
    StageStatus,
)
from asep.execution.state import (
    EXECUTION_TRANSITIONS,
    STAGE_TRANSITIONS,
    StateManager,
)
from asep.registry.loader import RegistryLoader
from asep.runtime.agent_runtime import AgentRuntime
from asep.workflow.loader import WorkflowLoader


def _competing_resume_worker(state_path: str, ready, start, results) -> None:
    manager = StateManager()
    path = Path(state_path)
    state = manager.load(path, expected_run_id=path.parent.name)
    ready.put("loaded")
    start.wait(10)
    try:
        manager.prepare_resume(state)
        manager.save(state, path)
        results.put(("saved", None))
    except Exception as exc:
        results.put(("error", type(exc).__name__))


def workflow_from(repository: Path):
    registry = RegistryLoader().load(repository / "registry")
    return WorkflowLoader().load(registry.workflows["software-project"], registry)


def new_state(repository: Path, filename: str = "state.yaml"):
    manager = StateManager()
    path = repository / filename
    state = manager.create(
        str(uuid4()), "sample", workflow_from(repository), path
    )
    return manager, state, path


@pytest.mark.parametrize("source", list(ExecutionStatus))
def test_all_declared_execution_transitions_accept_only_matrix_targets(
    sample_repository: Path, source: ExecutionStatus
) -> None:
    manager, base, _ = new_state(sample_repository, f"{source}.yaml")
    base.execution_status = source
    for target in ExecutionStatus:
        candidate = base.model_copy(deep=True)
        if target in EXECUTION_TRANSITIONS[source]:
            manager.transition_execution(candidate, target, "qa", "qa")
            assert candidate.execution_status == target
        else:
            with pytest.raises(StateTransitionError):
                manager.transition_execution(candidate, target, "qa", "qa")


@pytest.mark.parametrize("source", list(StageStatus))
def test_all_declared_stage_transitions_accept_only_matrix_targets(
    sample_repository: Path, source: StageStatus
) -> None:
    manager, base, _ = new_state(sample_repository, f"stage-{source}.yaml")
    base.stages[0].status = source
    for target in StageStatus:
        candidate = base.model_copy(deep=True)
        if target in STAGE_TRANSITIONS[source]:
            manager.transition_stage(candidate, "intake", target, "qa", "qa")
            assert candidate.stages[0].status == target
        else:
            with pytest.raises(StateTransitionError):
                manager.transition_stage(candidate, "intake", target, "qa", "qa")


def test_global_completed_is_accepted_while_stage_is_pending(
    sample_repository: Path,
) -> None:
    """Evidence QA-S2-001: não há validação de coerência global/etapas."""
    manager, state, _ = new_state(sample_repository)
    state.execution_status = ExecutionStatus.RUNNING
    assert state.stages[0].status == StageStatus.PENDING
    manager.transition_execution(state, ExecutionStatus.COMPLETED, "qa", "qa")
    assert state.execution_status == ExecutionStatus.COMPLETED
    assert state.stages[0].status == StageStatus.PENDING


def test_transition_history_survives_save_and_load(sample_repository: Path) -> None:
    manager, state, path = new_state(sample_repository)
    manager.transition_execution(state, ExecutionStatus.READY, "qa-ready", "qa")
    manager.save(state, path)
    loaded = manager.load(path, expected_run_id=state.run_id)
    assert len(loaded.transition_history) == 1
    assert loaded.transition_history[0].reason == "qa-ready"


def test_failed_save_keeps_old_snapshot_but_mutated_memory(
    sample_repository: Path, monkeypatch
) -> None:
    """Evidence QA-S2-002: falha não desfaz a mutação em memória."""
    manager, state, path = new_state(sample_repository)
    manager.transition_execution(state, ExecutionStatus.READY, "qa", "qa")

    def fail_replace(*args, **kwargs):
        raise OSError("fault injection")

    monkeypatch.setattr("asep.execution.state.os.replace", fail_replace)
    with pytest.raises(StatePersistenceError):
        manager.save(state, path)
    persisted = manager.load(path)
    assert persisted.execution_status == ExecutionStatus.CREATED
    assert state.execution_status == ExecutionStatus.READY


@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.AWAITING_APPROVAL,
        ExecutionStatus.COMPLETED,
        ExecutionStatus.CANCELLED,
    ],
)
def test_resume_rejects_non_resumable_states(
    sample_repository: Path, status: ExecutionStatus
) -> None:
    manager, state, _ = new_state(sample_repository)
    state.execution_status = status
    with pytest.raises(RunNotResumableError):
        manager.prepare_resume(state)


def test_state_accepts_artifact_reference_from_another_run(
    sample_repository: Path,
) -> None:
    """Evidence QA-S2-003: artifact_references é dict sem vínculo validado."""
    manager, state, path = new_state(sample_repository)
    other_run = str(uuid4())
    state.artifact_references.append(
        {
            "artifact_id": str(uuid4()),
            "run_id": other_run,
            "project_id": "other-project",
            "stage_id": "other-stage",
            "agent_id": "other-agent",
            "path": "foreign.md",
            "type": "markdown",
            "created_at": datetime.now(UTC).isoformat(),
            "checksum": "0" * 64,
        }
    )
    manager.save(state, path)
    loaded = manager.load(path)
    assert loaded.artifact_references[0]["run_id"] == other_run


def test_artifact_metadata_collision_is_silently_overwritten(
    tmp_path: Path,
) -> None:
    """Evidence QA-S2-004: colisão do sidecar não é verificada."""
    root = tmp_path / "artifacts"
    root.mkdir()
    sidecar = root / "summary.md.metadata.yaml"
    sidecar.write_text("owner: other-run\n", encoding="utf-8")
    ArtifactManager().persist(
        ArtifactDraft(relative_path="summary.md", content="# QA"),
        root,
        run_id=str(uuid4()),
        project_id="sample",
        stage_id="analysis",
        agent_id="business-analyst",
    )
    assert "owner: other-run" not in sidecar.read_text(encoding="utf-8")


def test_checksum_is_recorded_but_tampering_is_not_validated(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    reference = ArtifactManager().persist(
        ArtifactDraft(relative_path="summary.md", content="# Original"),
        root,
        run_id=str(uuid4()),
        project_id="sample",
        stage_id="analysis",
        agent_id="business-analyst",
    )
    (root / reference.path).write_text("# Alterado", encoding="utf-8")
    metadata = yaml.safe_load(
        (root / f"{reference.path}.metadata.yaml").read_text(encoding="utf-8")
    )
    assert metadata["checksum"] == reference.checksum
    assert not hasattr(ArtifactManager(), "validate")


def test_two_stale_writers_lose_first_update(sample_repository: Path) -> None:
    """Evidence QA-S2-005: ausência de lock/versionamento causa lost update."""
    manager, state, path = new_state(sample_repository)
    first = deepcopy(state)
    second = deepcopy(state)
    manager.transition_execution(first, ExecutionStatus.READY, "writer-one", "qa")
    manager.transition_execution(second, ExecutionStatus.READY, "writer-two", "qa")
    manager.save(first, path)
    manager.save(second, path)
    loaded = manager.load(path)
    reasons = [item.reason for item in loaded.transition_history]
    assert "writer-two" in reasons
    assert "writer-one" not in reasons


def test_two_processes_can_both_attempt_resume_same_run_id(
    sample_repository: Path,
) -> None:
    """Evidence QA-S2-007: não há rejeição explícita por lock single-writer."""
    run_id = str(uuid4())
    state_path = (
        sample_repository / "projects/sample/.asep/runs" / run_id / "state.yaml"
    )
    manager = StateManager()
    state = manager.create(
        run_id, "sample", workflow_from(sample_repository), state_path
    )
    state.execution_status = ExecutionStatus.BLOCKED
    state.stages[0].status = StageStatus.BLOCKED
    manager.save(state, state_path)

    context = multiprocessing.get_context("spawn")
    ready = context.Queue()
    start = context.Event()
    results = context.Queue()
    processes = [
        context.Process(
            target=_competing_resume_worker,
            args=(str(state_path), ready, start, results),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    ready.get(timeout=20)
    ready.get(timeout=20)
    start.set()
    outcomes = [results.get(timeout=20), results.get(timeout=20)]
    for process in processes:
        process.join(timeout=20)

    print(f"competing_resume_outcomes={outcomes}")
    assert all(process.exitcode == 0 for process in processes)
    assert not any(
        outcome == ("error", "RunNotResumableError") for outcome in outcomes
    )
    assert any(outcome[0] == "saved" for outcome in outcomes)


def test_empty_workflow_is_accepted_by_sequential_engine(
    sample_repository: Path,
) -> None:
    """Evidence QA-S2-006: workflow vazio passa pela validação do engine."""
    workflow = workflow_from(sample_repository).model_copy(
        update={
            "stages": [],
            "stage_dependencies": {},
            "assigned_agents": {},
            "stage_quality_gates": {},
            "quality_gates": [],
        }
    )
    SequentialWorkflowEngine().validate(workflow)
    assert SequentialWorkflowEngine().ordered_stage_ids(workflow) == ()


def test_runtime_wraps_agent_exception(sample_repository: Path) -> None:
    class ExplodingAgent:
        id = "business-analyst"

        def execute(self, context):
            raise RuntimeError("secret detail")

    registry = RegistryLoader().load(sample_repository / "registry")
    context = AgentContext(
        run_id=str(uuid4()),
        project_id="sample",
        project_name="Sample",
        workflow_id="software-project",
        stage_id="intake",
        agent_id="business-analyst",
        started_at=datetime.now(UTC),
        objective="qa",
        scope_received="qa",
    )
    with pytest.raises(AgentExecutionError) as error:
        AgentRuntime({"business-analyst": ExplodingAgent()}).execute(
            context, registry, logging.getLogger("qa")
        )
    assert "secret detail" not in str(error.value)
