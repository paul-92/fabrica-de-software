import logging
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import yaml

from asep.application.stage_execution import StageExecutionService
from asep.execution.models import (
    AgentContext,
    AgentResult,
    AgentResultStatus,
    ArtifactDraft,
    ArtifactReference,
    GateDecision,
    GateResult,
    StageStatus,
)
from asep.registry.loader import RegistryLoader

RUN_ID = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"
NOW = datetime(2026, 7, 29, tzinfo=UTC)


def context() -> AgentContext:
    return AgentContext(
        run_id=RUN_ID,
        project_id="sample",
        project_name="Sample",
        workflow_id="software-project",
        stage_id="intake",
        agent_id="business-analyst",
        started_at=NOW,
        objective="Objetivo confirmado",
        scope_received="Escopo confirmado",
    )


def result(status: AgentResultStatus) -> AgentResult:
    artifacts = (
        [ArtifactDraft(relative_path="summary.md", content="# Summary")]
        if status == AgentResultStatus.COMPLETED
        else []
    )
    return AgentResult(
        status=status,
        agent_id="business-analyst",
        stage_id="intake",
        run_id=RUN_ID,
        started_at=NOW,
        finished_at=NOW,
        artifacts=artifacts,
    )


def reference(path: str, agent_id: str) -> ArtifactReference:
    return ArtifactReference(
        artifact_id=f"artifact-{agent_id}",
        run_id=RUN_ID,
        project_id="sample",
        stage_id="intake",
        agent_id=agent_id,
        path=path,
        type="yaml" if path.endswith(".yaml") else "markdown",
        created_at=NOW,
        checksum="0" * 64,
    )


def test_blocked_result_returns_without_artifacts_or_gate(
    sample_repository: Path, tmp_path: Path
) -> None:
    blocked = result(AgentResultStatus.BLOCKED)
    runtime = Mock()
    runtime.execute.return_value = blocked
    artifacts = Mock()
    gates = Mock()
    registry = RegistryLoader().load(sample_repository / "registry")

    report = StageExecutionService(runtime, artifacts, gates).execute(
        context(),
        registry,
        tmp_path,
        "QG-INTAKE",
        StageStatus.RUNNING,
        logging.getLogger("test"),
    )

    assert report.agent_result == blocked
    assert report.artifact_references == ()
    assert report.gate_result is None
    assert report.gate_artifact_reference is None
    artifacts.persist.assert_not_called()
    gates.evaluate.assert_not_called()


def test_completed_result_persists_artifacts_evaluates_and_persists_gate(
    sample_repository: Path, tmp_path: Path
) -> None:
    completed = result(AgentResultStatus.COMPLETED)
    agent_reference = reference("summary.md", "business-analyst")
    gate_reference = reference(
        "quality-gates/intake-result.yaml", "quality-gate-engine"
    )
    gate = GateResult(
        gate_id="QG-INTAKE",
        run_id=RUN_ID,
        stage_id="intake",
        decision=GateDecision.APPROVED,
        satisfied_criteria=["resultado válido"],
        unsatisfied_criteria=[],
        evaluated_at=NOW,
    )
    runtime = Mock()
    runtime.execute.return_value = completed
    artifacts = Mock()
    artifacts.persist.side_effect = [agent_reference, gate_reference]
    gates = Mock()
    gates.evaluate.return_value = gate
    registry = RegistryLoader().load(sample_repository / "registry")

    report = StageExecutionService(runtime, artifacts, gates).execute(
        context(),
        registry,
        tmp_path,
        "QG-INTAKE",
        StageStatus.RUNNING,
        logging.getLogger("test"),
    )

    assert report.agent_result == completed
    assert report.artifact_references == (agent_reference,)
    assert report.gate_result == gate
    assert report.gate_artifact_reference == gate_reference
    assert artifacts.persist.call_count == 2
    gates.evaluate.assert_called_once_with(
        "QG-INTAKE",
        completed,
        [agent_reference],
        StageStatus.RUNNING,
    )

    gate_draft = artifacts.persist.call_args_list[1].args[0]
    assert gate_draft.relative_path == "quality-gates/intake-result.yaml"
    assert gate_draft.type == "yaml"
    assert yaml.safe_load(gate_draft.content)["decision"] == "APPROVED"
    assert artifacts.persist.call_args_list[1].kwargs["agent_id"] == (
        "quality-gate-engine"
    )
