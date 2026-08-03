"""Testes do Intelligent Orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.agents import (
    AgentError,
    AgentExecutionResult,
    AgentExecutionStatus,
    AgentId,
)
from asep.agents.coordination import (
    CoordinationResult,
    CoordinationStatistics,
    CoordinationStatus,
)
from asep.artifacts.manager import ArtifactManager
from asep.errors import ArtifactError
from asep.execution.models import (
    AgentResult,
    AgentResultStatus,
    ArtifactDraft,
   GateDecision, 
)
from asep.orchestrator.intelligent import (
    CoordinationArtifactCollector,
)

NOW = datetime(2026, 8, 3, 8, 0, tzinfo=UTC)


def coordination_result_with_artifact() -> CoordinationResult:
    """Cria um resultado de coordenação com um artefato pendente."""

    agent_result = AgentResult(
        status=AgentResultStatus.COMPLETED,
        agent_id="developer",
        stage_id="implementation",
        run_id="run-intelligent",
        started_at=NOW,
        finished_at=NOW,
        artifacts=[
            ArtifactDraft(
                relative_path="src/example.py",
                type="python",
                content='print("ASEP")\n',
            )
        ],
        messages=["Arquivo produzido."],
    )

    execution_result = AgentExecutionResult(
        execution_id="execution-1",
        agent_id=AgentId(value="developer"),
        status=AgentExecutionStatus.SUCCEEDED,
        output=agent_result.model_dump(mode="json"),
        started_at=NOW,
        completed_at=NOW,
        duration_seconds=0,
        attempts=1,
        metadata={},
        agent_result=agent_result,
    )

    return CoordinationResult(
        plan_id="plan-1",
        run_id="run-intelligent",
        status=CoordinationStatus.COMPLETED,
        assignments=(),
        results=(execution_result,),
        output={},
        statistics=CoordinationStatistics(
            assignments_total=1,
            completed_total=1,
            failed_total=0,
            agents_used=1,
            duration_seconds=0,
            aggregation_duration_seconds=0,
        ),
    )


def test_collector_persists_coordination_artifacts(
    tmp_path: Path,
) -> None:
    collector = CoordinationArtifactCollector()

    references = collector.persist(
        coordination_result_with_artifact(),
        tmp_path,
        run_id="run-intelligent",
        project_id="project-1",
    )

    assert len(references) == 1

    reference = references[0]

    assert reference.run_id == "run-intelligent"
    assert reference.project_id == "project-1"
    assert reference.stage_id == "implementation"
    assert reference.agent_id == "developer"
    assert reference.path == "src/example.py"
    assert reference.type == "python"
    assert reference.checksum

    artifact_path = tmp_path / "src" / "example.py"
    metadata_path = tmp_path / "src" / "example.py.metadata.yaml"

    assert artifact_path.is_file()
    assert metadata_path.is_file()
    assert artifact_path.read_text(encoding="utf-8") == (
        'print("ASEP")\n'
    )


def test_collector_ignores_execution_without_agent_result(
    tmp_path: Path,
) -> None:
    execution_result = AgentExecutionResult(
        
        execution_id="execution-without-result",
        agent_id=AgentId(value="developer"),
        status=AgentExecutionStatus.FAILED,
        output={},
        started_at=NOW,
        completed_at=NOW,
        duration_seconds=0,
        attempts=1,
        error=AgentError(
            code="execution_failed",
            message="Falha esperada no teste.",
),
        metadata={},
        agent_result=None,
    )

    coordination_result = CoordinationResult(
        plan_id="plan-empty",
        run_id="run-empty",
        status=CoordinationStatus.FAILED,
        assignments=(),
        results=(execution_result,),
        output={},
        statistics=CoordinationStatistics(
            assignments_total=1,
            completed_total=0,
            failed_total=1,
            agents_used=1,
            duration_seconds=0,
            aggregation_duration_seconds=0,
        ),
    )

    references = CoordinationArtifactCollector().persist(
        coordination_result,
        tmp_path,
        run_id="run-empty",
        project_id="project-1",
    )

    assert references == ()
    assert tuple(tmp_path.rglob("*")) == ()


def test_collector_preserves_artifact_collision_policy(
    tmp_path: Path,
) -> None:
    collector = CoordinationArtifactCollector(
        artifact_manager=ArtifactManager(),
    )
    coordination_result = coordination_result_with_artifact()

    collector.persist(
        coordination_result,
        tmp_path,
        run_id="run-intelligent",
        project_id="project-1",
    )

    with pytest.raises(ArtifactError):
        collector.persist(
            coordination_result,
            tmp_path,
            run_id="run-intelligent",
            project_id="project-1",
        )

from asep.business_engineering import (
    BusinessDescription,
    ProjectBlueprint,
)
from asep.orchestrator.intelligent import IntelligentOrchestratorService
from asep.orchestrator.models import (
    IntelligentExecutionRequest,
    IntelligentExecutionStatus,
)
from asep.planning import (
    ExecutionPlan,
    PlanningResult,
    PlanningStatistics,
)


class SpyPlanningAdapter:
    """Planning Adapter determinístico para testar o orquestrador."""

    def __init__(self) -> None:
        self.received_blueprint: ProjectBlueprint | None = None

    def create_execution_plan(
        self,
        blueprint: ProjectBlueprint,
    ) -> PlanningResult:
        self.received_blueprint = blueprint

        return PlanningResult(
            plan=ExecutionPlan(
                plan_id="plan-intelligent",
                goal=blueprint.description,
                steps=(),
                estimated_cost=0,
                estimated_duration_seconds=0,
                created_at=NOW,
            ),
            warnings=(),
            validation_messages=("Plano validado.",),
            statistics=PlanningStatistics(
                total_steps=0,
                dependency_count=0,
                maximum_depth=0,
                estimated_cost=0,
                estimated_duration_seconds=0,
                memory_entries_considered=0,
            ),
        )


class SpyCoordinatorAdapter:
    """Coordinator Adapter determinístico para testar o orquestrador."""

    def __init__(self) -> None:
        self.received_planning_result: PlanningResult | None = None

    def coordinate(
        self,
        planning_result: PlanningResult,
    ) -> CoordinationResult:
        self.received_planning_result = planning_result

        return CoordinationResult(
            plan_id=planning_result.plan.plan_id,
            run_id="run-intelligent",
            status=CoordinationStatus.COMPLETED,
            assignments=(),
            results=(),
            output={},
            statistics=CoordinationStatistics(
                assignments_total=0,
                completed_total=0,
                failed_total=0,
                agents_used=0,
                duration_seconds=0,
                aggregation_duration_seconds=0,
            ),
        )


class SpyArtifactCollector:
    """Artifact Collector determinístico para testar o orquestrador."""

    def __init__(self) -> None:
        self.received_coordination_result: CoordinationResult | None = None
        self.received_artifacts_root: Path | None = None
        self.received_run_id: str | None = None
        self.received_project_id: str | None = None

    def persist(
        self,
        coordination_result: CoordinationResult,
        artifacts_root: Path,
        *,
        run_id: str,
        project_id: str,
    ) -> tuple:
        self.received_coordination_result = coordination_result
        self.received_artifacts_root = artifacts_root
        self.received_run_id = run_id
        self.received_project_id = project_id

        return ()


def test_intelligent_orchestrator_executes_pipeline(
    tmp_path: Path,
) -> None:
    planning_adapter = SpyPlanningAdapter()
    coordinator_adapter = SpyCoordinatorAdapter()
    artifact_collector = SpyArtifactCollector()

    orchestrator = IntelligentOrchestratorService(
        planning_adapter=planning_adapter,
        coordinator_adapter=coordinator_adapter,
        artifact_collector=artifact_collector,
    )

    request = IntelligentExecutionRequest(
        run_id="run-intelligent",
        project_id="project-1",
        project_name="CRM",
        gate_id="default-quality-gate",
        description=BusinessDescription(
            text="O sistema deve cadastrar clientes."
        ),
        artifacts_root=tmp_path,
        metadata={
            "source": "test",
        },
    )

    result = orchestrator.execute(request)

    assert planning_adapter.received_blueprint is not None
    assert planning_adapter.received_blueprint.project_name == "CRM"

    assert coordinator_adapter.received_planning_result is not None
    assert (
        coordinator_adapter.received_planning_result.plan.plan_id
        == "plan-intelligent"
    )

    assert artifact_collector.received_coordination_result is not None
    assert (
        artifact_collector.received_coordination_result.plan_id
        == "plan-intelligent"
    )
    assert artifact_collector.received_artifacts_root == tmp_path
    assert artifact_collector.received_run_id == "run-intelligent"
    assert artifact_collector.received_project_id == "project-1"

    assert result.run_id == "run-intelligent"
    assert result.project_id == "project-1"
    assert result.status is IntelligentExecutionStatus.COMPLETED

    assert result.blueprint is not None
    assert result.blueprint.project_name == "CRM"

    assert result.planning_result is not None
    assert result.planning_result.plan.plan_id == "plan-intelligent"

    assert result.coordination_result is not None
    assert result.coordination_result.status is CoordinationStatus.COMPLETED

    assert result.artifact_references == ()
    assert result.errors == ()
    assert result.metadata == {
        "source": "test",
    }

def test_intelligent_orchestrator_is_blocked_when_quality_gate_blocks(
    tmp_path: Path,
) -> None:
    planning_adapter = SpyPlanningAdapter()

    class BlockingCoordinatorAdapter:
        def coordinate(
            self,
            planning_result: PlanningResult,
        ) -> CoordinationResult:
            del planning_result
            return coordination_result_with_artifact()

    class EmptyArtifactCollector:
        def persist(
            self,
            coordination_result: CoordinationResult,
            artifacts_root: Path,
            *,
            run_id: str,
            project_id: str,
        ) -> tuple:
            del (
                coordination_result,
                artifacts_root,
                run_id,
                project_id,
            )
            return ()

    orchestrator = IntelligentOrchestratorService(
        planning_adapter=planning_adapter,
        coordinator_adapter=BlockingCoordinatorAdapter(),
        artifact_collector=EmptyArtifactCollector(),
    )

    request = IntelligentExecutionRequest(
        run_id="run-intelligent",
        project_id="project-1",
        project_name="CRM",
        gate_id="default-quality-gate",
        description=BusinessDescription(
            text="O sistema deve cadastrar clientes."
        ),
        artifacts_root=tmp_path,
    )

    result = orchestrator.execute(request)

    assert len(result.gate_results) == 1
    assert result.gate_results[0].decision is GateDecision.BLOCKED
    assert result.status is IntelligentExecutionStatus.BLOCKED