from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asep.api import (
    SequentialOperationalApiComposition,
    create_default_app,
    create_default_operational_composition,
    create_sequential_operational_api_composition,
)
from asep.application import AuthorizedSequentialProject
from asep.orchestrator import Orchestrator

ROUTE = "/api/v1/sequential-projects/sample/executions/{}/quality-gates"
OPENAPI_ROUTE = (
    "/api/v1/sequential-projects/{project_id}/executions/"
    "{execution_id}/quality-gates"
)


def test_factory_returns_app_and_exact_executable_orchestrator(
    sample_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asep.api.composition as api_composition

    project_path = sample_repository / "projects" / "sample"
    original = api_composition.create_sequential_operational_composition
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        api_composition,
        "create_sequential_operational_composition",
        counted,
    )
    composition = create_sequential_operational_api_composition(
        authorized_projects=(AuthorizedSequentialProject("sample", project_path),),
        authorized_roots=(sample_repository / "projects",),
    )
    assert isinstance(composition, SequentialOperationalApiComposition)
    assert isinstance(composition.orchestrator, Orchestrator)
    assert calls == 1
    assert OPENAPI_ROUTE in composition.app.openapi()["paths"]


def test_execution_is_observable_through_same_operational_graph(
    sample_repository: Path,
) -> None:
    project_path = sample_repository / "projects" / "sample"
    run_id = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"
    composition = create_sequential_operational_api_composition(
        authorized_projects=(AuthorizedSequentialProject("sample", project_path),),
        authorized_roots=(sample_repository / "projects",),
    )

    composition.orchestrator.execute(
        project_path, run_id, logging.getLogger("test-sequential-quality-api")
    )
    response = TestClient(composition.app).get(ROUTE.format(run_id))

    assert response.status_code == 200
    assert response.json()["items"]
    assert all(item["execution_id"] == run_id for item in response.json()["items"])


def test_independent_compositions_are_isolated(sample_repository: Path) -> None:
    project_path = sample_repository / "projects" / "sample"
    registration = (AuthorizedSequentialProject("sample", project_path),)
    roots = (sample_repository / "projects",)
    first = create_sequential_operational_api_composition(
        authorized_projects=registration, authorized_roots=roots
    )
    second = create_sequential_operational_api_composition(
        authorized_projects=registration, authorized_roots=roots
    )
    run_id = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"
    first.orchestrator.execute(
        project_path, run_id, logging.getLogger("test-sequential-isolation")
    )
    assert TestClient(first.app).get(ROUTE.format(run_id)).status_code == 200
    assert TestClient(second.app).get(ROUTE.format(run_id)).status_code == 200
    # Both can see canonical state on disk, but only the producing graph has gates.
    assert TestClient(first.app).get(ROUTE.format(run_id)).json()["items"]
    assert TestClient(second.app).get(ROUTE.format(run_id)).json() == {"items": []}


def test_route_is_opt_in_and_agent_operational_composition_is_unchanged() -> None:
    route = OPENAPI_ROUTE
    assert route not in create_default_app().openapi()["paths"]
    agent_composition = create_default_operational_composition()
    assert route not in agent_composition.app.openapi()["paths"]
    assert "/api/v1/agents/runtime" in agent_composition.app.openapi()["paths"]
