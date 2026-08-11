"""Project-scoped read adapter over canonical ExecutionState YAML files."""

from __future__ import annotations

from asep.application.sequential_executions import (
    SequentialExecution,
    SequentialExecutionNotFoundError,
    SequentialExecutionOwnershipError,
)
from asep.application.sequential_projects import SequentialProjectResolver
from asep.execution.state import StateManager


class ProjectScopedSequentialExecutionSource:
    def __init__(
        self,
        project_resolver: SequentialProjectResolver,
        state_manager: StateManager,
    ) -> None:
        self._project_resolver = project_resolver
        self._state_manager = state_manager

    def get(self, project_id: str, execution_id: str) -> SequentialExecution:
        if not project_id.strip() or not execution_id.strip():
            raise ValueError("project_id e execution_id nao podem ser vazios")
        project_path = self._project_resolver.resolve(project_id).project_path

        runs_root = (project_path / ".asep" / "runs").resolve()
        state_path = (runs_root / execution_id / "state.yaml").resolve()
        if runs_root not in state_path.parents:
            raise SequentialExecutionNotFoundError(
                "Execucao sequencial nao encontrada."
            )
        if not state_path.is_file():
            raise SequentialExecutionNotFoundError(
                f"Execucao sequencial nao encontrada: {execution_id}"
            )

        state = self._state_manager.load(state_path, expected_run_id=execution_id)
        if state.project_id != project_id:
            raise SequentialExecutionOwnershipError(
                "Execucao sequencial pertence a outro projeto."
            )
        return SequentialExecution.from_state(state)


__all__ = ["ProjectScopedSequentialExecutionSource"]
