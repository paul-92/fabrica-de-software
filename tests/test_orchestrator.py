import logging
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from asep.agents.business_analyst import BusinessAnalystAgent
from asep.application.execution_bootstrap import (
    ExecutionBootstrap,
    ExecutionBootstrapResult,
)
from asep.application.stage_execution import (
    StageExecutionReport,
    StageExecutionService,
)
from asep.artifacts.manager import ArtifactManager
from asep.errors import ArtifactError
from asep.execution.engine import SequentialWorkflowEngine
from asep.execution.models import (
    AgentResult,
    AgentResultStatus,
    ArtifactReference,
    ExecutionState,
    ExecutionStatus,
    GateDecision,
    GateResult,
    RunContext,
    StageState,
    StageStatus,
)
from asep.execution.state import StateManager
from asep.orchestrator.service import Orchestrator
from asep.project.loader import ProjectLoader
from asep.quality.engine import QualityGateEngine
from asep.registry.loader import RegistryLoader
from asep.runtime.agent_runtime import AgentRuntime
from asep.workflow.loader import WorkflowLoader

RUN_ID = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"
NOW = datetime(2026, 7, 29, tzinfo=UTC)


def orchestrator_with_spies(sample_repository: Path):
    project_loader = ProjectLoader()
    registry_loader = RegistryLoader()
    workflow_loader = WorkflowLoader()
    workflow_engine = SequentialWorkflowEngine()
    state_manager = StateManager()
    runtime = AgentRuntime({"business-analyst": BusinessAnalystAgent()})
    artifact_manager = ArtifactManager()
    gate_engine = QualityGateEngine()
    bootstrap = Mock(
        spec=ExecutionBootstrap,
        wraps=ExecutionBootstrap(
            project_loader,
            registry_loader,
            workflow_loader,
            workflow_engine,
            state_manager,
        ),
    )
    stage_execution = Mock(
        spec=StageExecutionService,
        wraps=StageExecutionService(
            runtime,
            artifact_manager,
            gate_engine,
        ),
    )
    orchestrator = Orchestrator(
        project_loader=project_loader,
        registry_loader=registry_loader,
        workflow_loader=workflow_loader,
        workflow_engine=workflow_engine,
        state_manager=state_manager,
        agent_runtime=runtime,
        artifact_manager=artifact_manager,
        gate_engine=gate_engine,
        execution_bootstrap=bootstrap,
        stage_execution_service=stage_execution,
    )
    return orchestrator, bootstrap, stage_execution, state_manager


def test_orchestrator_prepares_without_executing_agents(
    sample_repository: Path,
) -> None:
    result = Orchestrator().prepare(
        sample_repository / "projects/sample",
        logging.getLogger("asep-test"),
    )

    assert result.project_id == "sample"
    assert result.workflow_id == "software-project"
    assert result.stage_ids == ("intake",)
    assert result.loaded_components["agents"] == 2
    assert result.artifact_count == 2
    assert result.warnings == ()


def test_run_delegates_bootstrap_and_stage_and_completes(
    sample_repository: Path,
) -> None:
    orchestrator, bootstrap, stage_execution, _state_manager = (
        orchestrator_with_spies(sample_repository)
    )
    project_path = sample_repository / "projects/sample"

    outcome = orchestrator.execute(
        project_path,
        RUN_ID,
        logging.getLogger("orchestrator-run-test"),
    )

    bootstrap.prepare.assert_called_once_with(project_path, RUN_ID)
    stage_execution.execute_stage.assert_called_once()
    assert outcome.status == ExecutionStatus.COMPLETED
    assert outcome.completed_stages == ("intake",)


def test_blocked_stage_preserves_run_id(sample_repository: Path) -> None:
    orchestrator, bootstrap, stage_execution, _state_manager = (
        orchestrator_with_spies(sample_repository)
    )
    project_path = sample_repository / "projects/sample"
    (project_path / "business-analysis/scope.md").unlink()

    outcome = orchestrator.execute(
        project_path,
        RUN_ID,
        logging.getLogger("orchestrator-blocked-test"),
    )

    bootstrap.prepare.assert_called_once_with(project_path, RUN_ID)
    stage_execution.execute_stage.assert_called_once()
    assert outcome.run_id == RUN_ID
    assert outcome.status == ExecutionStatus.BLOCKED


def test_controlled_failure_transitions_execution_to_failed(
    sample_repository: Path,
) -> None:
    orchestrator, _bootstrap, stage_execution, state_manager = (
        orchestrator_with_spies(sample_repository)
    )
    project_path = sample_repository / "projects/sample"
    stage_execution.execute_stage.side_effect = ArtifactError("fault injection")

    with pytest.raises(ArtifactError, match="fault injection"):
        orchestrator.execute(
            project_path,
            RUN_ID,
            logging.getLogger("orchestrator-failed-test"),
        )

    state_path = (
        project_path / ".asep/runs" / RUN_ID / "state.yaml"
    )
    state = state_manager.load(state_path, expected_run_id=RUN_ID)
    assert state.execution_status == ExecutionStatus.FAILED
    assert state.errors == ["fault injection"]


def test_resume_reuses_existing_state_and_skips_completed_stage(
    sample_repository: Path,
) -> None:
    project_loader = ProjectLoader()
    project = project_loader.load(sample_repository / "projects/sample")
    registry = RegistryLoader().load(sample_repository / "registry")
    workflow = WorkflowLoader().load(
        registry.workflows["software-project"],
        registry,
    )
    review_stage = workflow.stages[0].model_copy(
        update={"id": "review"}
    )
    resumed_workflow = workflow.model_copy(
        update={
            "stages": [workflow.stages[0], review_stage],
            "stage_dependencies": {
                "intake": [],
                "review": ["intake"],
            },
            "assigned_agents": {
                "intake": ["business-analyst"],
                "review": ["business-analyst"],
            },
            "stage_quality_gates": {
                "intake": "QG-INTAKE",
                "review": "QG-INTAKE",
            },
        }
    )
    state_path = project.path / ".asep/runs" / RUN_ID / "state.yaml"
    artifacts_path = project.path / "artifacts/runs" / RUN_ID
    state = ExecutionState(
        run_id=RUN_ID,
        project_id="sample",
        workflow_id="software-project",
        execution_status=ExecutionStatus.BLOCKED,
        current_stage="review",
        created_at=NOW,
        updated_at=NOW,
        stages=[
            StageState(
                id="intake",
                status=StageStatus.COMPLETED,
                agent_id="business-analyst",
                quality_gate_id="QG-INTAKE",
                attempts=1,
            ),
            StageState(
                id="review",
                status=StageStatus.BLOCKED,
                agent_id="business-analyst",
                quality_gate_id="QG-INTAKE",
                attempts=1,
            ),
        ],
    )
    state_manager = StateManager()
    state_manager.save(state, state_path)
    run_context = RunContext(
        run_id=RUN_ID,
        project_id="sample",
        workflow_id="software-project",
        started_at=NOW,
        current_stage="review",
        execution_status=ExecutionStatus.BLOCKED,
        project_path=project.path,
        state_path=state_path,
        artifacts_path=artifacts_path,
        logs_path=project.path / "logs/runs" / f"{RUN_ID}.jsonl",
    )
    bootstrap = Mock(spec=ExecutionBootstrap)
    bootstrap.resume.return_value = ExecutionBootstrapResult(
        project=project,
        registry=registry,
        workflow=resumed_workflow,
        run_context=run_context,
        state=state,
    )
    agent_result = AgentResult(
        status=AgentResultStatus.COMPLETED,
        agent_id="business-analyst",
        stage_id="review",
        run_id=RUN_ID,
        started_at=NOW,
        finished_at=NOW,
    )
    gate = GateResult(
        gate_id="QG-INTAKE",
        run_id=RUN_ID,
        stage_id="review",
        decision=GateDecision.APPROVED,
        satisfied_criteria=["valid"],
        unsatisfied_criteria=[],
        evaluated_at=NOW,
    )
    gate_reference = ArtifactReference(
        artifact_id="gate-reference",
        run_id=RUN_ID,
        project_id="sample",
        stage_id="review",
        agent_id="quality-gate-engine",
        path="quality-gates/review-result.yaml",
        type="yaml",
        created_at=NOW,
        checksum="0" * 64,
    )
    stage_execution = Mock(spec=StageExecutionService)
    stage_execution.execute_stage.return_value = StageExecutionReport(
        agent_result=agent_result,
        gate_result=gate,
        gate_artifact_reference=gate_reference,
    )
    orchestrator = Orchestrator(
        workflow_engine=SequentialWorkflowEngine(),
        state_manager=state_manager,
        execution_bootstrap=bootstrap,
        stage_execution_service=stage_execution,
    )

    outcome = orchestrator.resume(
        state_path,
        logging.getLogger("orchestrator-resume-test"),
    )

    bootstrap.resume.assert_called_once_with(state_path)
    stage_execution.execute_stage.assert_called_once()
    executed_stage = stage_execution.execute_stage.call_args.args[2]
    assert executed_stage.id == "review"
    assert state.stages[0].attempts == 1
    assert outcome.run_id == RUN_ID
    assert outcome.status == ExecutionStatus.COMPLETED
    assert outcome.completed_stages == ("intake", "review")
