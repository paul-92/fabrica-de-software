from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from asep.errors import RunNotFoundError
from asep.runs import (
    FileRunRepository,
    InMemoryRunRepository,
    Run,
    RunRepository,
    RunStatus,
    SQLiteRunRepository,
)

START = datetime(2026, 7, 30, 10, 0, tzinfo=UTC)


def run(
    run_id: str,
    *,
    status: RunStatus = RunStatus.PENDING,
    started_at: datetime = START,
    **values,
) -> Run:
    return Run(
        id=run_id,
        status=status,
        started_at=started_at,
        **values,
    )


@pytest.fixture(params=["memory", "file", "sqlite"])
def repository(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> RunRepository:
    factories: dict[str, Callable[[], RunRepository]] = {
        "memory": InMemoryRunRepository,
        "file": lambda: FileRunRepository(tmp_path / "runs.json"),
        "sqlite": lambda: SQLiteRunRepository(tmp_path / "asep.db"),
    }
    return factories[request.param]()


def test_contract_starts_empty(repository: RunRepository) -> None:
    assert repository.list() == ()


def test_contract_saves_and_gets_snapshot(
    repository: RunRepository,
) -> None:
    source = run("run")

    repository.save(source)
    restored = repository.get("run")

    assert restored == source
    assert restored is not source


def test_contract_updates_same_id(repository: RunRepository) -> None:
    repository.save(run("run", status=RunStatus.RUNNING))
    updated = run(
        "run",
        status=RunStatus.SUCCEEDED,
        finished_at=START + timedelta(seconds=1),
    )

    repository.save(updated)

    assert repository.get("run") == updated
    assert repository.list() == (updated,)


def test_contract_get_missing_uses_domain_error(
    repository: RunRepository,
) -> None:
    with pytest.raises(RunNotFoundError, match="missing"):
        repository.get("missing")


def test_contract_lists_by_started_at_then_id(
    repository: RunRepository,
) -> None:
    repository.save(run("z"))
    repository.save(run("old", started_at=START - timedelta(seconds=1)))
    repository.save(run("a"))

    assert tuple(item.id for item in repository.list()) == (
        "old",
        "a",
        "z",
    )


def test_contract_does_not_expose_internal_objects(
    repository: RunRepository,
) -> None:
    repository.save(run("run", metadata={"nested": {"value": 1}}))

    first = repository.get("run")
    second = repository.get("run")

    assert first is not second
    assert first.metadata is not second.metadata
    assert first.metadata["nested"] is not second.metadata["nested"]
