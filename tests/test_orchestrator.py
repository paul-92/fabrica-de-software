import logging
from pathlib import Path

from asep.orchestrator.service import Orchestrator


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
