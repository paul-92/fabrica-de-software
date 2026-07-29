from pathlib import Path

import pytest

from asep.errors import WorkflowValidationError
from asep.registry.loader import RegistryLoader
from asep.workflow.loader import WorkflowLoader


def test_workflow_loader_validates_registered_references(
    sample_repository: Path,
) -> None:
    registry = RegistryLoader().load(sample_repository / "registry")

    workflow = WorkflowLoader().load(
        registry.workflows["software-project"], registry
    )

    assert [stage.id for stage in workflow.stages] == ["intake"]
    assert workflow.assigned_agents["intake"] == ["business-analyst"]


def test_workflow_loader_rejects_unknown_agent(sample_repository: Path) -> None:
    path = sample_repository / "workflows/software-project.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "intake: [business-analyst]", "intake: [unknown-agent]"
        ),
        encoding="utf-8",
    )
    registry = RegistryLoader().load(sample_repository / "registry")

    with pytest.raises(WorkflowValidationError, match="Agentes não registrados"):
        WorkflowLoader().load(registry.workflows["software-project"], registry)


def test_workflow_loader_rejects_cycle(sample_repository: Path) -> None:
    path = sample_repository / "workflows/software-project.yaml"
    content = path.read_text(encoding="utf-8")
    path.write_text(
        content.replace("intake: []", "intake: [intake]"),
        encoding="utf-8",
    )
    registry = RegistryLoader().load(sample_repository / "registry")

    with pytest.raises(WorkflowValidationError, match="Ciclo"):
        WorkflowLoader().load(registry.workflows["software-project"], registry)
