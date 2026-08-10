from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.application import (
    AgentCatalogEntry,
    AgentCatalogService,
    AgentCatalogSource,
)
from asep.errors import AgentCatalogUnavailableError
from asep.registry.agent_catalog_source import DeclarativeAgentCatalogSource


class Source:
    def __init__(self, *items: AgentCatalogEntry) -> None:
        self.items = items
        self.calls = 0

    def list_agents(self) -> tuple[AgentCatalogEntry, ...]:
        self.calls += 1
        return self.items


def entry(agent_id: str, capability: str) -> AgentCatalogEntry:
    return AgentCatalogEntry(
        agent_id=agent_id,
        name=agent_id.title(),
        version="1.0",
        lifecycle_status="active",
        department="Engineering",
        capabilities=(capability,),
    )


def test_application_projection_is_immutable_safe_and_sorted() -> None:
    source = Source(entry("zeta", "review"), entry("alpha", "analysis"))

    result = AgentCatalogService(source).list_agents()

    assert isinstance(source, AgentCatalogSource)
    assert [item.agent_id for item in result] == ["alpha", "zeta"]
    assert result[0].model_dump() == {
        "agent_id": "alpha",
        "name": "Alpha",
        "version": "1.0",
        "lifecycle_status": "active",
        "department": "Engineering",
        "capabilities": ("analysis",),
    }
    assert set(AgentCatalogEntry.model_fields) == {
        "agent_id", "name", "version", "lifecycle_status",
        "department", "capabilities",
    }
    with pytest.raises(ValidationError):
        AgentCatalogEntry(
            agent_id="duplicate", name="Duplicate", version="1",
            lifecycle_status="active", department="Engineering",
            capabilities=("review", "review"),
        )


def test_application_allows_an_empty_catalog() -> None:
    source = Source()
    assert AgentCatalogService(source).list_agents() == ()
    assert source.calls == 1


def test_declarative_adapter_projects_only_approved_fields(
    sample_repository: Path,
) -> None:
    result = DeclarativeAgentCatalogSource(
        sample_repository / "registry"
    ).list_agents()

    assert {item.agent_id for item in result} == {
        "orchestrator", "business-analyst"
    }
    analyst = next(item for item in result if item.agent_id == "business-analyst")
    assert analyst.name == "Business Analyst"
    assert analyst.lifecycle_status == "active"
    assert analyst.department == "Business"
    assert analyst.capabilities == ("analysis",)
    serialized = str([item.model_dump() for item in result]).casefold()
    for forbidden in (
        "contract", "manual", "path", "prompt", "tool", "policy",
        "applicable_project_types", "dependencies",
    ):
        assert forbidden not in serialized


def test_declarative_adapter_allows_a_valid_empty_registry(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "registry"
    registry.mkdir()
    documents = {
        "agents.yaml": "version: '1'\nagents: []\n",
        "contracts.yaml": "version: '1'\ncontracts: []\n",
        "workflows.yaml": "version: '1'\nworkflows: []\n",
        "quality-gates.yaml": "version: '1'\nquality_gates: []\n",
        "playbooks.yaml": "version: '1'\nplaybooks: []\n",
        "knowledge.yaml": "version: '1'\nknowledge: []\n",
    }
    for name, content in documents.items():
        (registry / name).write_text(content, encoding="utf-8")

    assert DeclarativeAgentCatalogSource(registry).list_agents() == ()


def test_declarative_adapter_controls_invalid_catalog_errors(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "invalid-registry"
    registry.mkdir()
    (registry / "agents.yaml").write_text("agents: [", encoding="utf-8")

    with pytest.raises(
        AgentCatalogUnavailableError,
        match="could not be loaded",
    ) as error:
        DeclarativeAgentCatalogSource(registry).list_agents()

    assert str(registry) not in str(error.value)


def test_adapter_source_does_not_depend_on_agent_runtime() -> None:
    source = Path("src/asep/registry/agent_catalog_source.py").read_text(
        encoding="utf-8"
    )
    assert "asep.agents" not in source
    assert ".execute(" not in source
    assert "InMemoryAgentRegistry" not in source
