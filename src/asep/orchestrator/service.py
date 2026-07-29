"""Primeiro Orchestrator executável da ASEP."""

from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter

from asep.agents.business_analyst import BusinessAnalystAgent
from asep.application.execution_bootstrap import ExecutionBootstrap
from asep.application.stage_execution import StageExecutionService
from asep.artifacts.manager import ArtifactManager
from asep.errors import AsepError, ConsistencyError
from asep.execution.engine import SequentialWorkflowEngine
from asep.execution.models import (
    AgentResult,
    AgentResultStatus,
    ExecutionOutcome,
    ExecutionState,
    ExecutionStatus,
    GateDecision,
    StageState,
    StageStatus,
)
from asep.execution.state import StateManager
from asep.models import LoadedProject, PreparationResult, RegistrySnapshot, WorkflowDefinition
from asep.project.loader import ProjectLoader
from asep.quality.engine import QualityGateEngine
from asep.registry.loader import RegistryLoader
from asep.runtime.agent_runtime import AgentRuntime
from asep.workflow.loader import WorkflowLoader


class Orchestrator:
    """Carrega, valida e prepara uma execução sem iniciar agentes."""

    def __init__(
        self,
        project_loader: ProjectLoader | None = None,
        registry_loader: RegistryLoader | None = None,
        workflow_loader: WorkflowLoader | None = None,
        workflow_engine: SequentialWorkflowEngine | None = None,
        state_manager: StateManager | None = None,
        agent_runtime: AgentRuntime | None = None,
        artifact_manager: ArtifactManager | None = None,
        gate_engine: QualityGateEngine | None = None,
        stage_execution_service: StageExecutionService | None = None,
        execution_bootstrap: ExecutionBootstrap | None = None,
    ) -> None:
        self._project_loader = project_loader or ProjectLoader()
        self._registry_loader = registry_loader or RegistryLoader()
        self._workflow_loader = workflow_loader or WorkflowLoader()
        self._workflow_engine = workflow_engine or SequentialWorkflowEngine()
        self._state_manager = state_manager or StateManager()
        self._agent_runtime = agent_runtime or AgentRuntime(
            {"business-analyst": BusinessAnalystAgent()}
        )
        self._artifact_manager = artifact_manager or ArtifactManager()
        self._gate_engine = gate_engine or QualityGateEngine()
        self._stage_execution_service = (
            stage_execution_service
            or StageExecutionService(
                self._agent_runtime,
                self._artifact_manager,
                self._gate_engine,
            )
        )
        self._execution_bootstrap = (
            execution_bootstrap
            or ExecutionBootstrap(
                self._project_loader,
                self._registry_loader,
                self._workflow_loader,
                self._workflow_engine,
                self._state_manager,
            )
        )

    def prepare(self, project_path: Path, logger: logging.Logger) -> PreparationResult:
        started = perf_counter()
        logger.info("Iniciando preparação.", extra={"event_type": "orchestrator.started"})

        project = self._project_loader.load(project_path)
        repository_root = self._project_loader.find_repository_root(project.path)
        logger.info(
            "Projeto carregado.",
            extra={"event_type": "project.loaded", "project_id": project.definition.id},
        )

        registry = self._registry_loader.load(repository_root / "registry")
        logger.info(
            "Registry carregado.",
            extra={"event_type": "registry.loaded", "project_id": project.definition.id},
        )

        workflow_entry = registry.workflows.get(project.definition.workflow_id)
        if workflow_entry is None:
            raise ConsistencyError(
                f"Workflow do projeto não existe no Registry: {project.definition.workflow_id}"
            )
        workflow = self._workflow_loader.load(workflow_entry, registry)
        if project.definition.project_type not in workflow.applicable_project_types:
            raise ConsistencyError(
                f"Workflow {workflow.id} não se aplica ao tipo "
                f"{project.definition.project_type}."
            )

        warnings = tuple(
            f"Etapa {stage.id} usa modo {stage.mode}; Sprint 1 apenas prepara o fluxo."
            for stage in workflow.stages
            if stage.mode != "sequential"
        )
        for warning in warnings:
            logger.warning(
                warning,
                extra={
                    "event_type": "workflow.mode_warning",
                    "project_id": project.definition.id,
                    "workflow_id": workflow.id,
                },
            )

        elapsed = perf_counter() - started
        logger.info(
            "Preparação concluída; nenhum agente foi executado.",
            extra={
                "event_type": "orchestrator.completed",
                "project_id": project.definition.id,
                "workflow_id": workflow.id,
                "elapsed_seconds": round(elapsed, 6),
            },
        )
        return PreparationResult(
            project_id=project.definition.id,
            workflow_id=workflow.id,
            project_status=project.definition.status,
            stage_ids=tuple(stage.id for stage in workflow.stages),
            loaded_components={
                "agents": len(registry.agents),
                "contracts": len(registry.contracts),
                "workflows": len(registry.workflows),
                "quality_gates": len(registry.quality_gates),
                "playbooks": len(registry.playbooks),
                "knowledge": len(registry.knowledge),
            },
            artifact_count=len(project.markdown_artifacts),
            warnings=warnings,
            elapsed_seconds=elapsed,
        )

    def execute(
        self, project_path: Path, run_id: str, logger: logging.Logger
    ) -> ExecutionOutcome:
        bootstrap = self._execution_bootstrap.prepare(project_path, run_id)
        project = bootstrap.project
        registry = bootstrap.registry
        workflow = bootstrap.workflow
        run_context = bootstrap.run_context
        state = bootstrap.state
        logger.info(
            "Execução criada.",
            extra={
                "event_type": "run_created",
                "project_id": project.definition.id,
                "workflow_id": workflow.id,
            },
        )
        self._state_manager.transition_execution(
            state, ExecutionStatus.READY, "Entradas carregadas e validadas.", "orchestrator"
        )
        self._state_manager.transition_execution(
            state, ExecutionStatus.RUNNING, "Execução sequencial iniciada.", "orchestrator"
        )
        self._state_manager.save(state, run_context.state_path)
        self._log_state_change(state, logger, "execution")
        logger.info(
            "Execução iniciada.",
            extra={
                "event_type": "run_started",
                "project_id": project.definition.id,
                "workflow_id": workflow.id,
            },
        )
        return self._run_workflow(
            project,
            registry,
            workflow,
            state,
            run_context.state_path,
            run_context.artifacts_path,
            logger,
        )

    def resume(self, state_path: Path, logger: logging.Logger) -> ExecutionOutcome:
        bootstrap = self._execution_bootstrap.resume(state_path)
        project = bootstrap.project
        registry = bootstrap.registry
        workflow = bootstrap.workflow
        run_context = bootstrap.run_context
        state = bootstrap.state
        self._state_manager.prepare_resume(state)
        self._state_manager.save(state, state_path)
        logger.info(
            "Execução retomada.",
            extra={
                "event_type": "run_resumed",
                "project_id": state.project_id,
                "workflow_id": state.workflow_id,
            },
        )
        return self._run_workflow(
            project,
            registry,
            workflow,
            state,
            state_path,
            run_context.artifacts_path,
            logger,
        )

    def _run_workflow(
        self,
        project: LoadedProject,
        registry: RegistrySnapshot,
        workflow: WorkflowDefinition,
        state: ExecutionState,
        state_path: Path,
        artifacts_path: Path,
        logger: logging.Logger,
    ) -> ExecutionOutcome:
        try:
            while True:
                stage = self._workflow_engine.next_stage(workflow, state)
                if stage is None:
                    return self._finish_workflow(
                        state,
                        state_path,
                        artifacts_path,
                        logger,
                    )
                outcome = self._execute_current_stage(
                    project,
                    registry,
                    state,
                    stage,
                    state_path,
                    artifacts_path,
                    logger,
                )
                if outcome is not None:
                    return outcome
        except AsepError as exc:
            self._fail_execution(state, state_path, exc, logger)
            raise

    def _execute_current_stage(
        self,
        project: LoadedProject,
        registry: RegistrySnapshot,
        state: ExecutionState,
        stage: StageState,
        state_path: Path,
        artifacts_path: Path,
        logger: logging.Logger,
    ) -> ExecutionOutcome | None:
        self._start_stage(state, stage, state_path, logger)
        stage_report = self._stage_execution_service.execute_stage(
            project,
            state,
            stage,
            registry,
            artifacts_path,
            logger,
        )
        result = stage_report.agent_result
        if result.status != AgentResultStatus.COMPLETED:
            self._block_from_result(
                state,
                stage.id,
                result,
                state_path,
                logger,
            )
            return self._outcome(state, state_path, artifacts_path)

        state.artifact_references.extend(
            reference.model_dump(mode="json")
            for reference in stage_report.artifact_references
        )
        gate = stage_report.gate_result
        gate_reference = stage_report.gate_artifact_reference
        if gate is None or gate_reference is None:
            raise ConsistencyError(
                "Execução concluída da etapa não retornou quality gate."
            )
        state.artifact_references.append(
            gate_reference.model_dump(mode="json")
        )
        if gate.decision == GateDecision.BLOCKED:
            self._block_from_gate(state, stage.id, state_path, logger)
            return self._outcome(state, state_path, artifacts_path)

        self._state_manager.transition_stage(
            state,
            stage.id,
            StageStatus.COMPLETED,
            f"Quality gate {gate.decision}.",
            "orchestrator",
        )
        self._state_manager.save(state, state_path)
        self._log_state_change(state, logger, f"stage:{stage.id}")
        return None

    def _start_stage(
        self,
        state: ExecutionState,
        stage: StageState,
        state_path: Path,
        logger: logging.Logger,
    ) -> None:
        if stage.status == StageStatus.PENDING:
            self._state_manager.transition_stage(
                state,
                stage.id,
                StageStatus.READY,
                "Dependências concluídas.",
                "workflow-engine",
            )
            self._state_manager.save(state, state_path)
            self._log_state_change(state, logger, f"stage:{stage.id}")
            logger.info(
                "Etapa pronta.",
                extra={
                    "event_type": "stage_ready",
                    "project_id": state.project_id,
                    "workflow_id": state.workflow_id,
                    "stage_id": stage.id,
                },
            )
        self._state_manager.transition_stage(
            state,
            stage.id,
            StageStatus.RUNNING,
            "Execução da etapa iniciada.",
            "orchestrator",
        )
        self._state_manager.save(state, state_path)
        self._log_state_change(state, logger, f"stage:{stage.id}")
        logger.info(
            "Etapa iniciada.",
            extra={
                "event_type": "stage_started",
                "project_id": state.project_id,
                "workflow_id": state.workflow_id,
                "stage_id": stage.id,
            },
        )

    def _finish_workflow(
        self,
        state: ExecutionState,
        state_path: Path,
        artifacts_path: Path,
        logger: logging.Logger,
    ) -> ExecutionOutcome:
        if all(
            stage.status == StageStatus.COMPLETED for stage in state.stages
        ):
            self._complete_execution(state, state_path, logger)
        return self._outcome(state, state_path, artifacts_path)

    def _complete_execution(
        self,
        state: ExecutionState,
        state_path: Path,
        logger: logging.Logger,
    ) -> None:
        self._state_manager.transition_execution(
            state,
            ExecutionStatus.COMPLETED,
            "Todas as etapas foram concluídas.",
            "orchestrator",
        )
        self._state_manager.save(state, state_path)
        self._log_state_change(state, logger, "execution")
        logger.info(
            "Execução concluída.",
            extra={
                "event_type": "run_completed",
                "project_id": state.project_id,
                "workflow_id": state.workflow_id,
            },
        )

    def _block_from_gate(
        self,
        state: ExecutionState,
        stage_id: str,
        state_path: Path,
        logger: logging.Logger,
    ) -> None:
        self._state_manager.transition_stage(
            state,
            stage_id,
            StageStatus.BLOCKED,
            "Quality gate bloqueado.",
            "quality-gate-engine",
        )
        self._state_manager.transition_execution(
            state,
            ExecutionStatus.BLOCKED,
            "Quality gate bloqueado.",
            "orchestrator",
        )
        self._state_manager.save(state, state_path)
        self._log_state_change(state, logger, f"stage:{stage_id}")

    def _fail_execution(
        self,
        state: ExecutionState,
        state_path: Path,
        error: AsepError,
        logger: logging.Logger,
    ) -> None:
        if state.execution_status != ExecutionStatus.RUNNING:
            return
        self._state_manager.transition_execution(
            state,
            ExecutionStatus.FAILED,
            error.code,
            "orchestrator",
        )
        state.errors.append(error.message)
        self._state_manager.save(state, state_path)
        logger.error(
            "Execução falhou de forma controlada.",
            extra={
                "event_type": "run_failed",
                "project_id": state.project_id,
                "workflow_id": state.workflow_id,
            },
        )

    def _block_from_result(
        self,
        state: ExecutionState,
        stage_id: str,
        result: AgentResult,
        state_path: Path,
        logger: logging.Logger,
    ) -> None:
        target = (
            StageStatus.AWAITING_APPROVAL
            if result.status == AgentResultStatus.AWAITING_APPROVAL
            else StageStatus.BLOCKED
        )
        execution_target = (
            ExecutionStatus.AWAITING_APPROVAL
            if target == StageStatus.AWAITING_APPROVAL
            else ExecutionStatus.BLOCKED
        )
        self._state_manager.transition_stage(
            state, stage_id, target, "Agente reportou entradas pendentes.", "agent-runtime"
        )
        self._state_manager.transition_execution(
            state,
            execution_target,
            "Etapa não pode avançar.",
            "orchestrator",
        )
        state.errors.extend(result.errors)
        self._state_manager.save(state, state_path)
        self._log_state_change(state, logger, f"stage:{stage_id}")
        logger.warning(
            "Execução bloqueada.",
            extra={
                "event_type": "run_blocked",
                "project_id": state.project_id,
                "workflow_id": state.workflow_id,
                "stage_id": stage_id,
            },
        )

    @staticmethod
    def _outcome(
        state: ExecutionState, state_path: Path, artifacts_path: Path
    ) -> ExecutionOutcome:
        return ExecutionOutcome(
            run_id=state.run_id,
            project_id=state.project_id,
            workflow_id=state.workflow_id,
            status=state.execution_status,
            current_stage=state.current_stage,
            state_path=state_path,
            artifacts_path=artifacts_path,
            completed_stages=tuple(
                stage.id
                for stage in state.stages
                if stage.status == StageStatus.COMPLETED
            ),
        )

    @staticmethod
    def _log_state_change(
        state: ExecutionState, logger: logging.Logger, entity: str
    ) -> None:
        logger.info(
            "Estado alterado.",
            extra={
                "event_type": "state_changed",
                "project_id": state.project_id,
                "workflow_id": state.workflow_id,
                "stage_id": (
                    entity.removeprefix("stage:")
                    if entity.startswith("stage:")
                    else None
                ),
            },
        )
