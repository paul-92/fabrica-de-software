from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from asep.application.execution_bootstrap import (
    ExecutionBootstrap,
    ExecutionBootstrapResult,
)
from asep.errors import ConsistencyError
from asep.execution.engine import SequentialWorkflowEngine
from asep.execution.models import (
    ExecutionState,
    ExecutionStatus,
    StageState,
)
from asep.execution.state import StateManager
from asep.project.loader import ProjectLoader
from asep.registry.loader import RegistryLoader
from asep.workflow.loader import WorkflowLoader

RUN_ID = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"
NOW = datetime(2026, 7, 29, tzinfo=UTC)


def dependencies(sample_repository: Path):
    project = ProjectLoader().load(
        sample_repository / "projects" / "sample"
    )
    registry = RegistryLoader().load(sample_repository / "registry")
    workflow = WorkflowLoader().load(
        registry.workflows["software-project"], registry
    )
    state = ExecutionState(
        run_id=RUN_ID,
        project_id="sample",
        workflow_id="software-project",
        execution_status=ExecutionStatus.CREATED,
        current_stage=None,
        created_at=NOW,
        updated_at=NOW,
        stages=[
            StageState(
                id="intake",
                agent_id="business-analyst",
                quality_gate_id="QG-INTAKE",
            )
        ],
    )

    project_loader = Mock(spec=ProjectLoader)
    project_loader.load.return_value = project
    project_loader.find_repository_root.return_value = sample_repository
    registry_loader = Mock(spec=RegistryLoader)
    registry_loader.load.return_value = registry
    workflow_loader = Mock(spec=WorkflowLoader)
    workflow_loader.load.return_value = workflow
    workflow_engine = Mock(spec=SequentialWorkflowEngine)
    state_manager = Mock(spec=StateManager)
    state_manager.create.return_value = state
    bootstrap = ExecutionBootstrap(
        project_loader,
        registry_loader,
        workflow_loader,
        workflow_engine,
        state_manager,
    )
    return (
        bootstrap,
        project,
        registry,
        workflow,
        state,
        project_loader,
        registry_loader,
        workflow_loader,
        workflow_engine,
        state_manager,
    )


def test_prepares_valid_execution_with_expected_context_and_created_state(
    sample_repository: Path,
) -> None:
    (
        bootstrap,
        project,
        registry,
        workflow,
        state,
        project_loader,
        registry_loader,
        workflow_loader,
        workflow_engine,
        state_manager,
    ) = dependencies(sample_repository)
    project_path = sample_repository / "projects" / "sample"

    result = bootstrap.prepare(project_path, RUN_ID)

    assert result.project == project
    assert result.registry == registry
    assert result.workflow == workflow
    assert result.state == state
    assert result.state.execution_status == ExecutionStatus.CREATED
    assert result.run_context.execution_status == ExecutionStatus.CREATED
    assert result.run_context.current_stage is None
    project_loader.load.assert_called_once_with(project_path)
    project_loader.find_repository_root.assert_called_once_with(project.path)
    registry_loader.load.assert_called_once_with(
        sample_repository / "registry"
    )
    workflow_loader.load.assert_called_once_with(
        registry.workflows["software-project"], registry
    )
    workflow_engine.validate.assert_called_once_with(
        workflow,
        path=(
            registry.root
            / registry.workflows["software-project"].path
        ).resolve(),
    )
    state_manager.create.assert_called_once_with(
        RUN_ID,
        "sample",
        workflow,
        result.run_context.state_path,
    )


def test_builds_run_state_artifact_and_log_paths(
    sample_repository: Path,
) -> None:
    bootstrap, project, *_ = dependencies(sample_repository)

    result = bootstrap.prepare(project.path, RUN_ID)

    run_root = project.path / ".asep" / "runs" / RUN_ID
    assert result.run_context.state_path == run_root / "state.yaml"
    assert result.run_context.artifacts_path == (
        project.path / "artifacts" / "runs" / RUN_ID
    )
    assert result.run_context.logs_path == (
        project.path / "logs" / "runs" / f"{RUN_ID}.jsonl"
    )


def test_fails_when_project_workflow_is_not_registered(
    sample_repository: Path,
) -> None:
    (
        bootstrap,
        _project,
        registry,
        _workflow,
        _state,
        _project_loader,
        registry_loader,
        workflow_loader,
        workflow_engine,
        state_manager,
    ) = dependencies(sample_repository)
    registry_loader.load.return_value = registry.model_copy(
        update={"workflows": {}}
    )

    with pytest.raises(ConsistencyError, match="Workflow não registrado"):
        bootstrap.prepare(sample_repository / "projects/sample", RUN_ID)

    workflow_loader.load.assert_not_called()
    workflow_engine.validate.assert_not_called()
    state_manager.create.assert_not_called()


def test_fails_when_workflow_does_not_apply_to_project_type(
    sample_repository: Path,
) -> None:
    (
        bootstrap,
        _project,
        _registry,
        workflow,
        _state,
        _project_loader,
        _registry_loader,
        workflow_loader,
        workflow_engine,
        state_manager,
    ) = dependencies(sample_repository)
    workflow_loader.load.return_value = workflow.model_copy(
        update={"applicable_project_types": ["mobile"]}
    )

    with pytest.raises(ConsistencyError, match="não se aplica"):
        bootstrap.prepare(sample_repository / "projects/sample", RUN_ID)

    workflow_engine.validate.assert_not_called()
    state_manager.create.assert_not_called()


def test_bootstrap_result_rejects_unknown_fields(
    sample_repository: Path,
) -> None:
    bootstrap, project, registry, workflow, state, *_ = dependencies(
        sample_repository
    )
    prepared = bootstrap.prepare(project.path, RUN_ID)

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ExecutionBootstrapResult(
            project=project,
            registry=registry,
            workflow=workflow,
            run_context=prepared.run_context,
            state=state,
            unexpected=True,
        )
