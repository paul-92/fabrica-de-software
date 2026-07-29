import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.agents.business_analyst import BusinessAnalystAgent
from asep.errors import AgentNotFoundError, AgentResultError
from asep.execution.models import AgentContext, AgentResultStatus
from asep.registry.loader import RegistryLoader
from asep.runtime.agent_runtime import AgentRuntime


def context(agent_id: str = "business-analyst") -> AgentContext:
    return AgentContext(
        run_id="f2f1a9f1-2c60-4fa0-9120-6b9197589488",
        project_id="sample",
        project_name="Sample",
        workflow_id="software-project",
        stage_id="intake",
        agent_id=agent_id,
        started_at=datetime(2026, 7, 28, tzinfo=UTC),
        objective="Objetivo confirmado",
        scope_received="Escopo confirmado",
    )


def test_business_analyst_is_deterministic_and_creates_markdown() -> None:
    result = BusinessAnalystAgent().execute(context())

    assert result.status == AgentResultStatus.COMPLETED
    assert result.artifacts[0].relative_path.endswith(".md")
    assert result.run_id in result.artifacts[0].content


def test_business_analyst_blocks_without_required_input() -> None:
    result = BusinessAnalystAgent().execute(
        context().model_copy(update={"objective": None})
    )

    assert result.status == AgentResultStatus.BLOCKED
    assert result.artifacts == []
    assert result.metadata["missing_inputs"] == ["objective"]


def test_runtime_rejects_agent_without_adapter(sample_repository: Path) -> None:
    registry = RegistryLoader().load(sample_repository / "registry")

    with pytest.raises(AgentNotFoundError):
        AgentRuntime({}).execute(context(), registry, logging.getLogger("test"))


def test_runtime_rejects_result_with_wrong_identity(
    sample_repository: Path,
) -> None:
    class InvalidAgent:
        id = "business-analyst"

        def execute(self, agent_context):
            result = BusinessAnalystAgent().execute(agent_context)
            return result.model_copy(update={"run_id": "wrong"})

    registry = RegistryLoader().load(sample_repository / "registry")

    with pytest.raises(AgentResultError):
        AgentRuntime({"business-analyst": InvalidAgent()}).execute(
            context(), registry, logging.getLogger("test")
        )
