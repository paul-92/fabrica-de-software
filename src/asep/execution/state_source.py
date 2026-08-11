"""Project-scoped read adapter over canonical ExecutionState YAML files."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from asep.application.sequential_executions import (
    SequentialExecution,
    SequentialExecutionNotFoundError,
    SequentialExecutionOwnershipError,
)
from asep.execution.state import StateManager


class ProjectScopedSequentialExecutionSource:
    def __init__(
        self,
        project_paths: Mapping[str, Path],
        state_manager: StateManager,
    ) -> None:
        self._project_paths = {
            project_id: Path(path).resolve()
            for project_id, path in project_paths.items()
        }
        self._state_manager = state_manager

    def get(
        self,
        project_id: str,
        execution_id: str,
    ) -> SequentialExecution:
        if not project_id.strip() or not execution_id.strip():
            raise ValueError("project_id e execution_id não podem ser vazios")
        try:
            project_path = self._project_paths[project_id]
        except KeyError as exc:
            raise SequentialExecutionOwnershipError(
                f"Projeto não autorizado para execução sequencial: {project_id}"
            ) from exc

        runs_root = (project_path / ".asep" / "runs").resolve()
        state_path = (runs_root / execution_id / "state.yaml").resolve()
        if runs_root not in state_path.parents:
            raise SequentialExecutionNotFoundError(
                "Execução sequencial não encontrada."
            )
        if not state_path.is_file():
            raise SequentialExecutionNotFoundError(
                f"Execução sequencial não encontrada: {execution_id}",
                path=state_path,
            )

        state = self._state_manager.load(
            state_path,
            expected_run_id=execution_id,
        )
        if state.project_id != project_id:
            raise SequentialExecutionOwnershipError(
                "Execução sequencial pertence a outro projeto.",
                path=state_path,
            )
        return SequentialExecution.from_state(state)


__all__ = ["ProjectScopedSequentialExecutionSource"]
