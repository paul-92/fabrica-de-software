from __future__ import annotations

from dataclasses import FrozenInstanceError
import logging
from pathlib import Path

import pytest

from asep.orchestrator import (
    SequentialOperationalComposition,
    create_sequential_operational_composition,
)


def test_sequential_composition_is_frozen_and_exposes_query_source() -> None:
    composition = create_sequential_operational_composition()

    assert isinstance(composition, SequentialOperationalComposition)
    assert composition.quality_gate_results.list_by_run("run") == ()
    with pytest.raises(FrozenInstanceError):
        composition.orchestrator = composition.orchestrator  # type: ignore[misc]


def test_sequential_compositions_are_isolated() -> None:
    first = create_sequential_operational_composition()
    second = create_sequential_operational_composition()

    assert first.quality_gate_results is not second.quality_gate_results
    assert (
        first.sequential_execution_source
        is not second.sequential_execution_source
    )


def test_sequential_composition_exposes_shared_query_contracts() -> None:
    composition = create_sequential_operational_composition()

    assert composition.sequential_execution_source is not None
    assert composition.quality_gate_query is not None
    assert composition.quality_gate_results.list_by_run("run") == ()


def test_orchestrator_state_is_observable_through_composed_source(
    sample_repository: Path,
) -> None:
    project_path = sample_repository / "projects" / "sample"
    run_id = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"
    composition = create_sequential_operational_composition(
        project_paths={"sample": project_path}
    )

    outcome = composition.orchestrator.execute(
        project_path,
        run_id,
        logging.getLogger("test-quality-composition"),
    )

    observed = composition.sequential_execution_source.get("sample", run_id)
    projected = composition.quality_gate_query.get("sample", run_id)
    assert observed.execution_id == outcome.run_id
    assert observed.project_id == outcome.project_id
    assert projected.execution == observed
    assert projected.quality_gates == (
        composition.quality_gate_results.list_by_run(run_id)
    )
