from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from asep.execution.models import GateDecision
from asep.quality_results import (
    DuplicateQualityGateResultError,
    FileQualityGateResultRepository,
    InMemoryQualityGateResultRepository,
    InvalidQualityGateResultStorageFormatError,
    QualityGateResultRepository,
    SQLiteQualityGateResultRepository,
    StoredQualityGateResult,
)

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


def stored(
    *,
    run_id: str = "run-1",
    stage_id: str = "analysis",
    gate_id: str = "QG-ANALYSIS",
    decision: GateDecision = GateDecision.APPROVED,
    offset: int = 0,
) -> StoredQualityGateResult:
    return StoredQualityGateResult(
        gate_id=gate_id,
        run_id=run_id,
        stage_id=stage_id,
        decision=decision,
        satisfied_criteria=("artefato existe",),
        unsatisfied_criteria=("revisão pendente",),
        evaluated_at=NOW + timedelta(seconds=offset),
    )


def repositories(tmp_path: Path):
    return (
        InMemoryQualityGateResultRepository(),
        FileQualityGateResultRepository(tmp_path / "quality.json"),
        SQLiteQualityGateResultRepository(tmp_path / "quality.db"),
    )


@pytest.mark.parametrize("index", range(3))
def test_repository_contract_and_deterministic_run_isolation(
    tmp_path: Path, index: int
) -> None:
    repository = repositories(tmp_path)[index]
    assert isinstance(repository, QualityGateResultRepository)
    assert repository.list_by_run("missing") == ()

    later_stage = stored(stage_id="test", gate_id="QG-TEST", offset=2)
    first_stage = stored()
    other_run = stored(run_id="run-2", decision=GateDecision.BLOCKED)
    repository.record(later_stage)
    repository.record(other_run)
    repository.record(first_stage)

    results = repository.list_by_run("run-1")
    assert results == (first_stage, later_stage)
    assert repository.list_by_run("run-2") == (other_run,)
    assert results[0] is not first_stage


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("decision", list(GateDecision))
def test_all_decisions_and_criteria_round_trip(
    tmp_path: Path, index: int, decision: GateDecision
) -> None:
    repository = repositories(tmp_path)[index]
    result = stored(decision=decision)
    repository.record(result)
    assert repository.list_by_run(result.run_id) == (result,)


@pytest.mark.parametrize("index", range(3))
def test_duplicate_run_stage_gate_is_rejected(tmp_path: Path, index: int) -> None:
    repository = repositories(tmp_path)[index]
    result = stored()
    repository.record(result)
    with pytest.raises(DuplicateQualityGateResultError):
        repository.record(result.model_copy(update={"decision": GateDecision.BLOCKED}))


def test_file_repository_survives_reconstruction(tmp_path: Path) -> None:
    path = tmp_path / "quality.json"
    FileQualityGateResultRepository(path).record(stored())
    assert FileQualityGateResultRepository(path).list_by_run("run-1") == (stored(),)


def test_sqlite_repository_survives_reconstruction(tmp_path: Path) -> None:
    path = tmp_path / "quality.db"
    SQLiteQualityGateResultRepository(path).record(stored())
    assert SQLiteQualityGateResultRepository(path).list_by_run("run-1") == (stored(),)


def test_file_repository_rejects_malformed_storage(tmp_path: Path) -> None:
    path = tmp_path / "quality.json"
    path.write_text(json.dumps({"version": "1.0", "results": [{}]}), encoding="utf-8")
    with pytest.raises(InvalidQualityGateResultStorageFormatError):
        FileQualityGateResultRepository(path)


def test_sqlite_repository_rejects_malformed_payload(tmp_path: Path) -> None:
    path = tmp_path / "quality.db"
    repository = SQLiteQualityGateResultRepository(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO quality_gate_results VALUES (?, ?, ?, ?, ?)",
            ("run-1", "analysis", "QG-ANALYSIS", NOW.isoformat(), "{}"),
        )
    with pytest.raises(InvalidQualityGateResultStorageFormatError):
        repository.list_by_run("run-1")


def test_independent_memory_repositories_are_isolated() -> None:
    first = InMemoryQualityGateResultRepository()
    second = InMemoryQualityGateResultRepository()
    first.record(stored())
    assert second.list_by_run("run-1") == ()
