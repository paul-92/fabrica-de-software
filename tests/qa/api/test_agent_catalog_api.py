from pathlib import Path

from fastapi.testclient import TestClient

from asep.api import create_app, create_default_app
from asep.application import (
    AgentCatalogEntry,
    AgentCatalogService,
    RunQueryService,
)
from asep.configuration import ApplicationSettings
from asep.metrics import MetricsService
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository


class Source:
    def __init__(self, items: tuple[AgentCatalogEntry, ...]) -> None:
        self.items = items

    def list_agents(self) -> tuple[AgentCatalogEntry, ...]:
        return self.items


def item(agent_id: str, name: str) -> AgentCatalogEntry:
    return AgentCatalogEntry(
        agent_id=agent_id,
        name=name,
        version="0.1.0",
        lifecycle_status="active",
        department="Engineering",
        capabilities=("validate-inputs", "produce-evidence"),
    )


def client(*items: AgentCatalogEntry) -> TestClient:
    query = RunQueryService(
        InMemoryRunRepository(), InMemoryTimelineRepository()
    )
    return TestClient(create_app(
        query,
        MetricsService(query),
        agent_catalog_service=AgentCatalogService(Source(items)),
    ))


def test_agent_catalog_endpoint_is_valid_safe_and_sorted() -> None:
    response = client(
        item("zeta", "Zeta"), item("backend-engineer", "Backend Engineer")
    ).get("/api/v1/agents")

    assert response.status_code == 200
    assert response.json() == {"items": [
        {
            "agent_id": "backend-engineer",
            "name": "Backend Engineer",
            "version": "0.1.0",
            "lifecycle_status": "active",
            "department": "Engineering",
            "capabilities": ["validate-inputs", "produce-evidence"],
        },
        {
            "agent_id": "zeta",
            "name": "Zeta",
            "version": "0.1.0",
            "lifecycle_status": "active",
            "department": "Engineering",
            "capabilities": ["validate-inputs", "produce-evidence"],
        },
    ]}
    payload = response.text.casefold()
    for forbidden in (
        "contract", "manual", "filesystem", "python", "prompt", "tool",
        "policy", "runtime_context", "instance",
    ):
        assert forbidden not in payload


def test_agent_catalog_endpoint_allows_empty_catalog() -> None:
    assert client().get("/api/v1/agents").json() == {"items": []}


def test_invalid_catalog_returns_a_safe_public_error(tmp_path: Path) -> None:
    response = TestClient(create_default_app(ApplicationSettings(
        agent_catalog_directory=tmp_path / "missing-registry"
    ))).get("/api/v1/agents")

    assert response.status_code == 503
    assert response.json() == {"error": {
        "code": "AGENT_CATALOG_UNAVAILABLE",
        "message": "Agent catalog is unavailable.",
    }}
    assert str(tmp_path) not in response.text


def test_agent_catalog_openapi_contract_is_explicit() -> None:
    app = client().app
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/agents"]["get"]
    properties = schema["components"]["schemas"][
        "AgentCatalogItemResponse"
    ]["properties"]

    assert operation["responses"].keys() >= {"200", "503"}
    assert set(properties) == {
        "agent_id", "name", "version", "lifecycle_status",
        "department", "capabilities",
    }


def test_default_composition_exposes_declarative_catalog(
    sample_repository: Path,
) -> None:
    app = create_default_app(ApplicationSettings(
        agent_catalog_directory=sample_repository / "registry"
    ))
    response = TestClient(app).get("/api/v1/agents")

    assert response.status_code == 200
    assert [item["agent_id"] for item in response.json()["items"]] == [
        "business-analyst", "orchestrator"
    ]
