from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import yaml

from asep.application.stage_execution import StageExecutionService
from asep.artifacts.manager import ArtifactManager
from asep.execution.models import (
    GateDecision,
    GateResult,
)
from asep.execution_package import ExecutionPackage, ExecutionPackageBuilder
from asep.orchestrator.service import Orchestrator
from asep.prompting import PromptBuilder
from asep.providers import (
    AgentExecutionResult,
    AgentExecutionStatus,
    ProviderUnavailableError,
)
from asep.quality.engine import QualityGateEngine
from asep.runtime.agent_runtime import AgentRuntime

RUN_ID = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"


class ProviderFake:
    name = "fake"

    def __init__(
        self,
        result: AgentExecutionResult | None = None,
        *,
        unavailable: bool = False,
    ) -> None:
        self.result = result or AgentExecutionResult(
            status=AgentExecutionStatus.SUCCESS,
            provider_name=self.name,
            provider_version="1.0",
            exit_code=0,
            stdout="# Provider result\n\nExecution completed.\n",
        )
        self.unavailable = unavailable
        self.packages: list[ExecutionPackage] = []

    def execute(
        self, package: ExecutionPackage
    ) -> AgentExecutionResult:
        self.packages.append(package)
        if self.unavailable:
            raise ProviderUnavailableError("Provider fake indisponível.")
        return self.result


class BlockingGateEngine:
    def evaluate(self, gate_id, result, artifacts, stage_status):
        return GateResult(
            gate_id=gate_id,
            run_id=result.run_id,
            stage_id=result.stage_id,
            decision=GateDecision.BLOCKED,
            satisfied_criteria=[],
            unsatisfied_criteria=["revisão obrigatória"],
            evaluated_at=datetime.now(UTC),
        )


def test_complete_provider_flow_builds_once_persists_and_advances(
    sample_repository: Path,
) -> None:
    provider = ProviderFake()
    prompt_builder = Mock(spec=PromptBuilder, wraps=PromptBuilder())
    package_builder = Mock(
        spec=ExecutionPackageBuilder,
        wraps=ExecutionPackageBuilder(),
    )
    artifacts = ArtifactManager()
    gates = QualityGateEngine()
    stage_service = StageExecutionService(
        AgentRuntime({}),
        artifacts,
        gates,
        provider=provider,
        prompt_builder=prompt_builder,
        package_builder=package_builder,
    )
    project = sample_repository / "projects/sample"

    outcome = Orchestrator(
        artifact_manager=artifacts,
        gate_engine=gates,
        stage_execution_service=stage_service,
    ).execute(
        project,
        RUN_ID,
        logging.getLogger("provider-e2e-success"),
    )

    assert outcome.status == "completed"
    assert outcome.completed_stages == ("intake",)
    assert prompt_builder.build.call_count == 1
    assert package_builder.build.call_count == 1
    assert len(provider.packages) == 1

    execution_package = provider.packages[0]
    assert execution_package.manifest.run_id == RUN_ID
    assert execution_package.manifest.stage_id == "intake"
    assert execution_package.context.contract.id == "business-analyst"
    assert execution_package.task.startswith("# Tarefa")

    provider_artifact = (
        outcome.artifacts_path / "provider-results/intake-result.md"
    )
    gate_artifact = (
        outcome.artifacts_path / "quality-gates/intake-result.yaml"
    )
    assert provider_artifact.read_text(encoding="utf-8").startswith(
        "# Provider result"
    )
    assert gate_artifact.is_file()
    gate_document = yaml.safe_load(
        gate_artifact.read_text(encoding="utf-8")
    )
    assert gate_document["decision"] == "APPROVED"


def test_failed_provider_result_stops_workflow_without_artifacts(
    sample_repository: Path,
) -> None:
    provider = ProviderFake(
        AgentExecutionResult(
            status=AgentExecutionStatus.FAILED,
            provider_name="fake",
            provider_version="1.0",
            exit_code=1,
            stderr="provider failed",
            errors=("provider failed",),
        )
    )
    project = sample_repository / "projects/sample"

    outcome = Orchestrator(agent_provider=provider).execute(
        project,
        RUN_ID,
        logging.getLogger("provider-e2e-failed"),
    )

    state = yaml.safe_load(outcome.state_path.read_text(encoding="utf-8"))
    assert outcome.status == "failed"
    assert state["execution_status"] == "failed"
    assert state["stages"][0]["status"] == "failed"
    assert state["errors"] == ["provider failed"]
    assert not outcome.artifacts_path.exists()


def test_unavailable_provider_becomes_failed_report_and_state(
    sample_repository: Path,
) -> None:
    provider = ProviderFake(unavailable=True)

    outcome = Orchestrator(agent_provider=provider).execute(
        sample_repository / "projects/sample",
        RUN_ID,
        logging.getLogger("provider-e2e-unavailable"),
    )

    state = yaml.safe_load(outcome.state_path.read_text(encoding="utf-8"))
    assert outcome.status == "failed"
    assert state["stages"][0]["status"] == "failed"
    assert state["errors"] == ["Provider fake indisponível."]
    assert not outcome.artifacts_path.exists()


def test_blocked_quality_gate_persists_artifacts_and_blocks_advance(
    sample_repository: Path,
) -> None:
    provider = ProviderFake()
    gate_engine = BlockingGateEngine()
    project = sample_repository / "projects/sample"

    outcome = Orchestrator(
        agent_provider=provider,
        gate_engine=gate_engine,
    ).execute(
        project,
        RUN_ID,
        logging.getLogger("provider-e2e-blocked-gate"),
    )

    state = yaml.safe_load(outcome.state_path.read_text(encoding="utf-8"))
    assert outcome.status == "blocked"
    assert outcome.completed_stages == ()
    assert state["stages"][0]["status"] == "blocked"
    assert (
        outcome.artifacts_path / "provider-results/intake-result.md"
    ).is_file()
    gate_path = (
        outcome.artifacts_path / "quality-gates/intake-result.yaml"
    )
    assert yaml.safe_load(
        gate_path.read_text(encoding="utf-8")
    )["decision"] == "BLOCKED"


def test_provider_result_metadata_is_preserved_for_gate_input(
    sample_repository: Path,
) -> None:
    provider = ProviderFake(
        AgentExecutionResult(
            status=AgentExecutionStatus.SUCCESS,
            provider_name="fake",
            provider_version="2.0",
            exit_code=0,
            stdout="result",
            metadata={"trace_id": "trace-1"},
        )
    )
    gate_engine = Mock(spec=QualityGateEngine, wraps=QualityGateEngine())

    outcome = Orchestrator(
        agent_provider=provider,
        gate_engine=gate_engine,
    ).execute(
        sample_repository / "projects/sample",
        RUN_ID,
        logging.getLogger("provider-e2e-metadata"),
    )

    result_for_gate = gate_engine.evaluate.call_args.args[1]
    assert outcome.status == "completed"
    assert result_for_gate.metadata["provider_name"] == "fake"
    assert result_for_gate.metadata["provider_version"] == "2.0"
    assert result_for_gate.metadata["provider_status"] == "success"
    assert result_for_gate.metadata["provider_metadata"] == {
        "trace_id": "trace-1"
    }
