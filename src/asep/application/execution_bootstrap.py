"""Preparação dos insumos necessários para uma nova execução."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from asep.errors import ConsistencyError
from asep.execution.engine import SequentialWorkflowEngine
from asep.execution.models import (
    ExecutionState,
    ExecutionStatus,
    RunContext,
)
from asep.execution.state import StateManager
from asep.models import LoadedProject, RegistrySnapshot, WorkflowDefinition
from asep.project.loader import ProjectLoader
from asep.registry.loader import RegistryLoader
from asep.workflow.loader import WorkflowLoader


class ExecutionBootstrapResult(BaseModel):
    """Contexto validado e estado inicial de uma nova execução."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project: LoadedProject
    registry: RegistrySnapshot
    workflow: WorkflowDefinition
    run_context: RunContext
    state: ExecutionState


class ExecutionBootstrap:
    """Carrega, valida e cria o estado inicial antes do loop."""

    def __init__(
        self,
        project_loader: ProjectLoader,
        registry_loader: RegistryLoader,
        workflow_loader: WorkflowLoader,
        workflow_engine: SequentialWorkflowEngine,
        state_manager: StateManager,
    ) -> None:
        self._project_loader = project_loader
        self._registry_loader = registry_loader
        self._workflow_loader = workflow_loader
        self._workflow_engine = workflow_engine
        self._state_manager = state_manager

    def prepare(
        self, project_path: Path, run_id: str
    ) -> ExecutionBootstrapResult:
        project = self._project_loader.load(project_path)
        repository_root = self._project_loader.find_repository_root(
            project.path
        )
        registry = self._registry_loader.load(repository_root / "registry")

        workflow_entry = registry.workflows.get(
            project.definition.workflow_id
        )
        if workflow_entry is None:
            raise ConsistencyError(
                f"Workflow não registrado: {project.definition.workflow_id}"
            )
        workflow = self._workflow_loader.load(workflow_entry, registry)
        if (
            project.definition.project_type
            not in workflow.applicable_project_types
        ):
            raise ConsistencyError(
                f"Workflow {workflow.id} não se aplica a "
                f"{project.definition.project_type}."
            )

        workflow_path = (registry.root / workflow_entry.path).resolve()
        self._workflow_engine.validate(workflow, path=workflow_path)

        run_root = project.path / ".asep" / "runs" / run_id
        state_path = run_root / "state.yaml"
        artifacts_path = project.path / "artifacts" / "runs" / run_id
        logs_path = project.path / "logs" / "runs" / f"{run_id}.jsonl"
        run_context = RunContext(
            run_id=run_id,
            project_id=project.definition.id,
            workflow_id=workflow.id,
            started_at=datetime.now(UTC),
            current_stage=None,
            execution_status=ExecutionStatus.CREATED,
            project_path=project.path,
            state_path=state_path,
            artifacts_path=artifacts_path,
            logs_path=logs_path,
        )
        state = self._state_manager.create(
            run_id,
            project.definition.id,
            workflow,
            state_path,
        )
        return ExecutionBootstrapResult(
            project=project,
            registry=registry,
            workflow=workflow,
            run_context=run_context,
            state=state,
        )
