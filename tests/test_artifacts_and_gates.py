from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.artifacts.manager import ArtifactManager
from asep.errors import ArtifactError
from asep.execution.models import (
    AgentResult,
    AgentResultStatus,
    ArtifactDraft,
    ArtifactReference,
    GateDecision,
    StageStatus,
)
from asep.quality.engine import QualityGateEngine


def agent_result(*, warnings=(), errors=()) -> AgentResult:
    return AgentResult(
        status=AgentResultStatus.COMPLETED,
        agent_id="business-analyst",
        stage_id="analysis",
        run_id="f2f1a9f1-2c60-4fa0-9120-6b9197589488",
        started_at=datetime(2026, 7, 28, tzinfo=UTC),
        finished_at=datetime(2026, 7, 28, tzinfo=UTC),
        warnings=list(warnings),
        errors=list(errors),
    )


def reference(tmp_path: Path) -> ArtifactReference:
    return ArtifactManager().persist(
        ArtifactDraft(relative_path="summary.md", content="# Summary"),
        tmp_path,
        run_id="f2f1a9f1-2c60-4fa0-9120-6b9197589488",
        project_id="sample",
        stage_id="analysis",
        agent_id="business-analyst",
    )


def test_artifact_manager_persists_metadata_and_checksum(tmp_path: Path) -> None:
    artifact = reference(tmp_path)

    assert (tmp_path / artifact.path).is_file()
    assert (tmp_path / f"{artifact.path}.metadata.yaml").is_file()
    assert len(artifact.checksum) == 64


def test_artifact_manager_blocks_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ArtifactError):
        ArtifactManager().persist(
            ArtifactDraft(relative_path="../escape.md", content="unsafe"),
            tmp_path,
            run_id="f2f1a9f1-2c60-4fa0-9120-6b9197589488",
            project_id="sample",
            stage_id="analysis",
            agent_id="business-analyst",
        )


def test_quality_gate_approved(tmp_path: Path) -> None:
    result = QualityGateEngine().evaluate(
        "QG-ANALYSIS",
        agent_result(),
        [reference(tmp_path)],
        StageStatus.RUNNING,
    )
    assert result.decision == GateDecision.APPROVED


def test_quality_gate_approved_with_pending(tmp_path: Path) -> None:
    result = QualityGateEngine().evaluate(
        "QG-ANALYSIS",
        agent_result(warnings=["pendência não crítica"]),
        [reference(tmp_path)],
        StageStatus.RUNNING,
    )
    assert result.decision == GateDecision.APPROVED_WITH_PENDING


def test_quality_gate_blocked_without_artifact() -> None:
    result = QualityGateEngine().evaluate(
        "QG-ANALYSIS", agent_result(), [], StageStatus.RUNNING
    )
    assert result.decision == GateDecision.BLOCKED
