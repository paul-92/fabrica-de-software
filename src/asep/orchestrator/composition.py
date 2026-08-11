"""Explicit composition for sequential execution and Quality Gate results."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from pathlib import Path

from asep.application import (
    SequentialExecutionSource,
    SequentialQualityGateQueryService,
)
from asep.configuration import ApplicationSettings
from asep.execution.state import StateManager
from asep.execution.state_source import ProjectScopedSequentialExecutionSource
from asep.orchestrator.service import Orchestrator
from asep.quality_results import QualityGateResultRepository
from asep.repositories import RepositoryFactory


@dataclass(frozen=True, slots=True)
class SequentialOperationalComposition:
    orchestrator: Orchestrator
    sequential_execution_source: SequentialExecutionSource
    quality_gate_query: SequentialQualityGateQueryService
    quality_gate_results: QualityGateResultRepository


def create_sequential_operational_composition(
    settings: ApplicationSettings | None = None,
    *,
    project_paths: Mapping[str, Path] | None = None,
) -> SequentialOperationalComposition:
    repositories = RepositoryFactory(settings or ApplicationSettings()).create()
    quality_gate_results = repositories.quality_gate_result_repository
    state_manager = StateManager()
    sequential_execution_source = ProjectScopedSequentialExecutionSource(
        project_paths or {},
        state_manager,
    )
    return SequentialOperationalComposition(
        orchestrator=Orchestrator(
            state_manager=state_manager,
            quality_gate_results=quality_gate_results,
        ),
        sequential_execution_source=sequential_execution_source,
        quality_gate_query=SequentialQualityGateQueryService(
            sequential_execution_source,
            quality_gate_results,
        ),
        quality_gate_results=quality_gate_results,
    )


__all__ = [
    "SequentialOperationalComposition",
    "create_sequential_operational_composition",
]
