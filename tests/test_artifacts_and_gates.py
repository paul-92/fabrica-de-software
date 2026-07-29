from datetime import UTC, datetime
import os
from pathlib import Path
import tempfile

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


def test_artifact_manager_uses_short_unique_temporary_names_in_deep_path(
    tmp_path: Path, monkeypatch
) -> None:
    run_id = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"
    artifacts_root = tmp_path
    metadata_relative = Path(
        "business-analysis/execution-summary.md.metadata.yaml"
    )
    while len(str(artifacts_root / metadata_relative)) < 220:
        artifacts_root /= "deep-segment"

    created_temporaries: list[Path] = []
    original_mkstemp = tempfile.mkstemp

    def recording_mkstemp(*args, **kwargs):
        descriptor, name = original_mkstemp(*args, **kwargs)
        created_temporaries.append(Path(name))
        return descriptor, name

    monkeypatch.setattr(
        "asep.artifacts.manager.tempfile.mkstemp",
        recording_mkstemp,
    )

    artifact = ArtifactManager().persist(
        ArtifactDraft(
            relative_path="business-analysis/execution-summary.md",
            content="# Summary",
        ),
        artifacts_root,
        run_id=run_id,
        project_id="sample",
        stage_id="analysis",
        agent_id="business-analyst",
    )

    target = artifacts_root / artifact.path
    metadata = target.with_suffix(target.suffix + ".metadata.yaml")
    assert target.is_file()
    assert metadata.is_file()
    assert len(created_temporaries) == 2
    assert len({path.name for path in created_temporaries}) == 2
    assert all(path.parent == target.parent for path in created_temporaries)
    assert all(path.name.startswith(".asep-") for path in created_temporaries)
    assert all(run_id not in path.name for path in created_temporaries)
    assert all(target.name not in path.name for path in created_temporaries)
    assert all(metadata.name not in path.name for path in created_temporaries)
    assert all(not path.exists() for path in created_temporaries)


def test_artifact_manager_removes_temporary_files_after_metadata_failure(
    tmp_path: Path, monkeypatch
) -> None:
    replace_calls = 0
    original_replace = os.replace

    def fail_metadata_replace(source, target):
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("metadata fault injection")
        original_replace(source, target)

    monkeypatch.setattr(
        "asep.artifacts.manager.os.replace",
        fail_metadata_replace,
    )

    with pytest.raises(ArtifactError) as error:
        ArtifactManager().persist(
            ArtifactDraft(relative_path="summary.md", content="# Summary"),
            tmp_path,
            run_id="f2f1a9f1-2c60-4fa0-9120-6b9197589488",
            project_id="sample",
            stage_id="analysis",
            agent_id="business-analyst",
        )

    assert isinstance(error.value.__cause__, OSError)
    assert not (tmp_path / "summary.md").exists()
    assert not list(tmp_path.glob(".asep-*.tmp"))


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
