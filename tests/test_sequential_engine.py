from pathlib import Path

import pytest

from asep.errors import UnsupportedCapabilityError, WorkflowValidationError
from asep.execution.engine import SequentialWorkflowEngine
from asep.execution.models import ExecutionStatus
from asep.execution.state import StateManager
from asep.registry.loader import RegistryLoader
from asep.workflow.loader import WorkflowLoader


def loaded_workflow(sample_repository: Path):
    registry = RegistryLoader().load(sample_repository / "registry")
    return WorkflowLoader().load(registry.workflows["software-project"], registry)


@pytest.mark.parametrize("mode", ["parallel", "conditional"])
def test_engine_rejects_unsupported_mode(
    sample_repository: Path, mode: str
) -> None:
    workflow = loaded_workflow(sample_repository)
    stage = workflow.stages[0].model_copy(
        update={
            "mode": mode,
            "workflow": None if mode == "parallel" else "project-intake",
            "workflows": ["project-intake"] if mode == "parallel" else [],
        }
    )
    unsupported = workflow.model_copy(update={"stages": [stage]})

    with pytest.raises(UnsupportedCapabilityError):
        SequentialWorkflowEngine().validate(unsupported)


def test_engine_detects_cycle(sample_repository: Path) -> None:
    workflow = loaded_workflow(sample_repository).model_copy(
        update={"stage_dependencies": {"intake": ["intake"]}}
    )

    with pytest.raises(WorkflowValidationError, match="Ciclo"):
        SequentialWorkflowEngine().validate(workflow)


def test_engine_selects_next_stage(sample_repository: Path) -> None:
    workflow = loaded_workflow(sample_repository)
    state = StateManager().create(
        "f2f1a9f1-2c60-4fa0-9120-6b9197589488",
        "sample",
        workflow,
        sample_repository / "state.yaml",
    )
    state.execution_status = ExecutionStatus.RUNNING

    assert SequentialWorkflowEngine().next_stage(workflow, state).id == "intake"
