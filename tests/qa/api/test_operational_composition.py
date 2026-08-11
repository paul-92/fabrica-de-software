import inspect
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asep.api import (
    OperationalComposition,
    create_default_app,
    create_default_operational_composition,
)
from asep.configuration import ApplicationSettings
from asep.pipeline import ASEPEngine, PipelineBuilder, PipelineComposition


ENDPOINT = "/api/v1/agents/runtime"


def workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "docs" / "architecture").mkdir(parents=True)
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    (tmp_path / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "docs" / "architecture" / "ArchitectureMap.md").write_text(
        "# Architecture\nPipeline -> Runtime\n",
        encoding="utf-8",
    )
    return tmp_path


def runtime_count(client: TestClient) -> int:
    response = client.get(ENDPOINT)
    assert response.status_code == 200
    assert response.json()["items"][0]["agent_id"] == "developer"
    assert response.json()["items"][0]["registered"] is True
    return response.json()["items"][0]["execution_count"]


def test_factory_returns_frozen_app_and_engine_composition() -> None:
    composition = create_default_operational_composition(
        ApplicationSettings()
    )

    assert isinstance(composition, OperationalComposition)
    assert isinstance(composition.app, FastAPI)
    assert isinstance(composition.engine, ASEPEngine)
    assert ENDPOINT in composition.app.openapi()["paths"]
    with pytest.raises(FrozenInstanceError):
        composition.engine = composition.engine  # type: ignore[misc]


def test_http_projection_observes_execution_from_same_graph(
    tmp_path: Path,
) -> None:
    composition = create_default_operational_composition(
        ApplicationSettings()
    )
    client = TestClient(composition.app)

    assert runtime_count(client) == 0
    composition.engine.execute("Inspect.", workspace=workspace(tmp_path))
    assert runtime_count(client) == 4


def test_factory_builds_once_and_shares_the_pipeline_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    built: list[PipelineComposition] = []
    original = PipelineBuilder.build_composition

    def track_build(builder: PipelineBuilder) -> PipelineComposition:
        composition = original(builder)
        built.append(composition)
        return composition

    monkeypatch.setattr(PipelineBuilder, "build_composition", track_build)

    operational = create_default_operational_composition(
        ApplicationSettings()
    )
    client = TestClient(operational.app)

    assert len(built) == 1
    assert operational.engine is built[0].engine
    assert built[0].agent_metrics.snapshot().by_agent == {}
    operational.engine.execute("Inspect.", workspace=workspace(tmp_path))
    assert built[0].agent_metrics.snapshot().by_agent == {"developer": 4}
    assert runtime_count(client) == 4


def test_operational_compositions_are_isolated(tmp_path: Path) -> None:
    first = create_default_operational_composition(ApplicationSettings())
    second = create_default_operational_composition(ApplicationSettings())
    first_client = TestClient(first.app)
    second_client = TestClient(second.app)

    first.engine.execute("Inspect.", workspace=workspace(tmp_path))

    assert runtime_count(first_client) == 4
    assert runtime_count(second_client) == 0


def test_default_app_remains_non_operational_and_source_compatible() -> None:
    app = create_default_app(ApplicationSettings())

    assert isinstance(app, FastAPI)
    assert ENDPOINT not in app.openapi()["paths"]
    signature = inspect.signature(create_default_app)
    assert tuple(signature.parameters) == ("repository_settings",)


def test_http_route_layer_has_no_runtime_implementation_dependency() -> None:
    route_source = Path("src/asep/api/agent_routes.py").read_text(
        encoding="utf-8"
    )
    composition_source = Path("src/asep/api/composition.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "AgentRegistry",
        "AgentExecutionService",
        "InMemoryAgentExecutionMetrics",
        "InMemoryAgentRegistry",
    ):
        assert forbidden not in route_source
        assert forbidden not in composition_source
