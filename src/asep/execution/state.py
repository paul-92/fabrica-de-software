"""Persistência atômica e máquina de estados da execução."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import yaml
from pydantic import ValidationError

from asep.errors import (
    ConfigurationError,
    RunNotFoundError,
    RunNotResumableError,
    StatePersistenceError,
    StateTransitionError,
    describe_validation_error,
)
from asep.execution.models import (
    ExecutionState,
    ExecutionStatus,
    StageState,
    StageStatus,
    TransitionRecord,
)
from asep.models import WorkflowDefinition
from asep.yaml_io import load_yaml

EXECUTION_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.CREATED: {ExecutionStatus.READY},
    ExecutionStatus.READY: {ExecutionStatus.RUNNING},
    ExecutionStatus.RUNNING: {
        ExecutionStatus.AWAITING_APPROVAL,
        ExecutionStatus.BLOCKED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.COMPLETED,
    },
    ExecutionStatus.AWAITING_APPROVAL: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.BLOCKED,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.BLOCKED: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.FAILED: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.CANCELLED: set(),
    ExecutionStatus.COMPLETED: set(),
}

STAGE_TRANSITIONS: dict[StageStatus, set[StageStatus]] = {
    StageStatus.PENDING: {StageStatus.READY, StageStatus.CANCELLED},
    StageStatus.READY: {StageStatus.RUNNING, StageStatus.CANCELLED},
    StageStatus.RUNNING: {
        StageStatus.AWAITING_APPROVAL,
        StageStatus.BLOCKED,
        StageStatus.FAILED,
        StageStatus.CANCELLED,
        StageStatus.COMPLETED,
    },
    StageStatus.AWAITING_APPROVAL: {
        StageStatus.RUNNING,
        StageStatus.BLOCKED,
        StageStatus.CANCELLED,
    },
    StageStatus.BLOCKED: {StageStatus.RUNNING, StageStatus.CANCELLED},
    StageStatus.FAILED: {StageStatus.RUNNING, StageStatus.CANCELLED},
    StageStatus.SKIPPED: set(),
    StageStatus.CANCELLED: set(),
    StageStatus.COMPLETED: set(),
}


class StateManager:
    """Valida transições e persiste snapshots YAML por substituição atômica."""

    def create(
        self,
        run_id: str,
        project_id: str,
        workflow: WorkflowDefinition,
        state_path: Path,
        *,
        now: datetime | None = None,
    ) -> ExecutionState:
        self._validate_run_id(run_id)
        if state_path.exists():
            raise StatePersistenceError(
                "Execução já existe; sobrescrita recusada.", path=state_path
            )
        timestamp = now or datetime.now(UTC)
        state = ExecutionState(
            run_id=run_id,
            project_id=project_id,
            workflow_id=workflow.id,
            execution_status=ExecutionStatus.CREATED,
            current_stage=None,
            created_at=timestamp,
            updated_at=timestamp,
            stages=[
                StageState(
                    id=stage.id,
                    agent_id=workflow.assigned_agents[stage.id][0],
                    quality_gate_id=workflow.stage_quality_gates.get(stage.id),
                )
                for stage in workflow.stages
            ],
        )
        self.save(state, state_path)
        return state

    def load(self, state_path: Path, *, expected_run_id: str | None = None) -> ExecutionState:
        try:
            state = ExecutionState.model_validate(load_yaml(state_path))
        except ValidationError as exc:
            raise StatePersistenceError(
                f"Estado inválido: {describe_validation_error(exc)}", path=state_path
            ) from exc
        except ConfigurationError as exc:
            raise StatePersistenceError(
                f"Estado ilegível: {exc.message}", path=state_path
            ) from exc
        self._validate_run_id(state.run_id)
        if expected_run_id and state.run_id != expected_run_id:
            raise StatePersistenceError(
                "run_id do estado diverge da execução solicitada.", path=state_path
            )
        return state

    def save(self, state: ExecutionState, state_path: Path) -> None:
        state_path = state_path.resolve()
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_path.with_name(f".{state_path.name}.{state.run_id}.tmp")
        try:
            if state_path.is_file():
                existing = load_yaml(state_path)
                if existing.get("run_id") != state.run_id:
                    raise StatePersistenceError(
                        "Estado existente pertence a outra execução.",
                        path=state_path,
                    )
            serialized = yaml.safe_dump(
                state.model_dump(mode="json"),
                allow_unicode=True,
                sort_keys=False,
            )
            temporary.write_text(serialized, encoding="utf-8")
            ExecutionState.model_validate(load_yaml(temporary))
            os.replace(temporary, state_path)
        except StatePersistenceError:
            raise
        except (OSError, ValidationError, yaml.YAMLError, ConfigurationError) as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise StatePersistenceError(
                f"Falha na escrita atômica do estado: {exc}", path=state_path
            ) from exc

    def transition_execution(
        self,
        state: ExecutionState,
        new_status: ExecutionStatus,
        reason: str,
        component: str,
        *,
        now: datetime | None = None,
    ) -> None:
        previous = state.execution_status
        if new_status not in EXECUTION_TRANSITIONS[previous]:
            raise StateTransitionError(
                f"Transição de execução inválida: {previous} -> {new_status}"
            )
        timestamp = now or datetime.now(UTC)
        state.execution_status = new_status
        state.updated_at = timestamp
        state.transition_history.append(
            TransitionRecord(
                timestamp=timestamp,
                run_id=state.run_id,
                entity="execution",
                previous_state=previous,
                new_state=new_status,
                reason=reason,
                component=component,
            )
        )

    def transition_stage(
        self,
        state: ExecutionState,
        stage_id: str,
        new_status: StageStatus,
        reason: str,
        component: str,
        *,
        now: datetime | None = None,
    ) -> StageState:
        stage = self.stage(state, stage_id)
        previous = stage.status
        if new_status not in STAGE_TRANSITIONS[previous]:
            raise StateTransitionError(
                f"Transição de etapa inválida: {stage_id}: {previous} -> {new_status}"
            )
        timestamp = now or datetime.now(UTC)
        stage.status = new_status
        if new_status == StageStatus.RUNNING:
            stage.attempts += 1
        state.current_stage = stage_id
        state.updated_at = timestamp
        state.transition_history.append(
            TransitionRecord(
                timestamp=timestamp,
                run_id=state.run_id,
                entity=f"stage:{stage_id}",
                previous_state=previous,
                new_state=new_status,
                reason=reason,
                component=component,
            )
        )
        return stage

    @staticmethod
    def stage(state: ExecutionState, stage_id: str) -> StageState:
        for stage in state.stages:
            if stage.id == stage_id:
                return stage
        raise StateTransitionError(f"Etapa não existe no estado: {stage_id}")

    @staticmethod
    def last_completed_stage(state: ExecutionState) -> str | None:
        completed = [stage.id for stage in state.stages if stage.status == StageStatus.COMPLETED]
        return completed[-1] if completed else None

    def prepare_resume(
        self, state: ExecutionState, *, now: datetime | None = None
    ) -> None:
        if state.execution_status not in {
            ExecutionStatus.FAILED,
            ExecutionStatus.BLOCKED,
        }:
            raise RunNotResumableError(
                f"Execução em estado não retomável: {state.execution_status}"
            )
        timestamp = now or datetime.now(UTC)
        state.resumed_at = timestamp
        self.transition_execution(
            state,
            ExecutionStatus.RUNNING,
            "Retomada validada entre etapas.",
            "state-manager",
            now=timestamp,
        )

    @staticmethod
    def _validate_run_id(run_id: str) -> None:
        try:
            parsed = UUID(run_id)
        except ValueError as exc:
            raise StatePersistenceError(f"run_id inválido: {run_id}") from exc
        if parsed.version != 4:
            raise StatePersistenceError("run_id deve ser UUID v4.")


class RunLocator:
    """Localiza estados sem manter índice global ou usar dados externos."""

    def locate(self, workspace_root: Path, run_id: str) -> Path:
        StateManager._validate_run_id(run_id)
        candidates = list(
            workspace_root.resolve().glob(f"projects/*/.asep/runs/{run_id}/state.yaml")
        )
        if len(candidates) != 1:
            raise RunNotFoundError(
                f"Execução não encontrada de forma unívoca: {run_id}",
                path=workspace_root,
            )
        return candidates[0]
