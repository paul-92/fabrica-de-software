from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from asep.agents import AgentId
from asep.pipeline import ASEPEngine, PipelineBuilder, PipelineComposition


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


def test_build_remains_compatible_and_returns_engine() -> None:
    assert isinstance(PipelineBuilder().build(), ASEPEngine)


def test_build_composition_is_typed_frozen_and_registers_developer() -> None:
    composition = PipelineBuilder().build_composition()

    assert isinstance(composition, PipelineComposition)
    assert isinstance(composition.engine, ASEPEngine)
    assert composition.agent_registry.contains(AgentId(value="developer"))
    with pytest.raises(FrozenInstanceError):
        composition.engine = composition.engine  # type: ignore[misc]


def test_engine_execution_updates_composition_metrics(tmp_path: Path) -> None:
    composition = PipelineBuilder().build_composition()
    before = composition.agent_metrics.snapshot()

    result = composition.engine.execute(
        "Inspect the project.",
        workspace=workspace(tmp_path),
    )

    after = composition.agent_metrics.snapshot()
    assert before.by_agent == {}
    assert after.by_agent == {"developer": 4}
    assert result.metrics["agents"]["by_agent"] == {"developer": 4}


def test_pipeline_compositions_are_isolated(tmp_path: Path) -> None:
    first = PipelineBuilder().build_composition()
    second = PipelineBuilder().build_composition()

    assert first.agent_registry is not second.agent_registry
    assert first.agent_metrics is not second.agent_metrics
    first.engine.execute("Inspect.", workspace=workspace(tmp_path))
    assert first.agent_metrics.snapshot().by_agent == {"developer": 4}
    assert second.agent_metrics.snapshot().by_agent == {}

