"""Componentes do Intelligent Orchestrator."""

from __future__ import annotations

from pathlib import Path

from asep.agents.coordination import (
    AgentCoordinatorAdapter,
    CoordinationResult,
    CoordinationStatus,
)
from asep.artifacts.manager import ArtifactManager
from asep.business_engineering import (
    BlueprintBuilder,
    PlanningEngineAdapter,
)
from asep.execution.models import ArtifactReference
from asep.orchestrator.models import (
    IntelligentExecutionRequest,
    IntelligentExecutionResult,
    IntelligentExecutionStatus,
)

from asep.execution.models import (
    ArtifactReference,
    GateDecision,
    GateResult,
    StageStatus,
)
from asep.quality.engine import QualityGateEngine
class CoordinationArtifactCollector:
    """Coleta e persiste artefatos produzidos durante a coordenação."""

    def __init__(
        self,
        artifact_manager: ArtifactManager | None = None,
    ) -> None:
        self._artifact_manager = artifact_manager or ArtifactManager()

    def persist(
        self,
        coordination_result: CoordinationResult,
        artifacts_root: Path,
        *,
        run_id: str,
        project_id: str,
    ) -> tuple[ArtifactReference, ...]:
        """Persiste todos os ArtifactDraft presentes na coordenação."""

        references: list[ArtifactReference] = []

        for execution_result in coordination_result.results:
            agent_result = execution_result.agent_result

            if agent_result is None:
                continue

            for draft in agent_result.artifacts:
                reference = self._artifact_manager.persist(
                    draft,
                    artifacts_root,
                    run_id=run_id,
                    project_id=project_id,
                    stage_id=agent_result.stage_id,
                    agent_id=agent_result.agent_id,
                )
                references.append(reference)

        return tuple(references)


class IntelligentOrchestratorService:
    """Executa e consolida o pipeline inteligente da ASEP."""

    def __init__(
        self,
        planning_adapter: PlanningEngineAdapter,
        coordinator_adapter: AgentCoordinatorAdapter,
        *,
        blueprint_builder: BlueprintBuilder | None = None,
        artifact_collector: CoordinationArtifactCollector | None = None,
        quality_gate_engine: QualityGateEngine | None = None,
    ) -> None:
        self._blueprint_builder = blueprint_builder or BlueprintBuilder()
        self._planning_adapter = planning_adapter
        self._coordinator_adapter = coordinator_adapter
        self._artifact_collector = (
            artifact_collector or CoordinationArtifactCollector()
        )
        self._quality_gate_engine = (
            quality_gate_engine or QualityGateEngine()
        )

    def execute(
        self,
        request: IntelligentExecutionRequest,
    ) -> IntelligentExecutionResult:
        """Executa o pipeline inteligente e retorna o resultado consolidado."""

        blueprint = self._blueprint_builder.build(
            project_name=request.project_name,
            description=request.description,
        )

        planning_result = self._planning_adapter.create_execution_plan(
            blueprint
        )

        coordination_result = self._coordinator_adapter.coordinate(
            planning_result
        )

        artifact_references = self._artifact_collector.persist(
            coordination_result,
            request.artifacts_root,
            run_id=request.run_id,
            project_id=request.project_id,
        )

        gate_results = self._evaluate_quality_gates(
            coordination_result=coordination_result,
            artifact_references=artifact_references,
            gate_id=request.gate_id,
        )

        return IntelligentExecutionResult(
            run_id=request.run_id,
            project_id=request.project_id,
            status=self._execution_status(
                coordination_result.status,
                gate_results,
            ),
            blueprint=blueprint,
            planning_result=planning_result,
            coordination_result=coordination_result,
            artifact_references=artifact_references,
            gate_results=gate_results,
            metadata=dict(request.metadata),
        )

    def _evaluate_quality_gates(
        self,
        *,
        coordination_result: CoordinationResult,
        artifact_references: tuple[ArtifactReference, ...],
        gate_id: str,
    ) -> tuple[GateResult, ...]:
        gate_results: list[GateResult] = []

        for execution_result in coordination_result.results:
            agent_result = execution_result.agent_result

            if agent_result is None:
                continue

            stage_artifacts = [
                reference
                for reference in artifact_references
                if reference.stage_id == agent_result.stage_id
            ]

            gate_result = self._quality_gate_engine.evaluate(
                gate_id=gate_id,
                result=agent_result,
                artifacts=stage_artifacts,
                stage_status=StageStatus.RUNNING,
            )

            gate_results.append(gate_result)

        return tuple(gate_results)

    @staticmethod
    def _execution_status(
        coordination_status: CoordinationStatus,
        gate_results: tuple[GateResult, ...],
    ) -> IntelligentExecutionStatus:
        if any(
            gate_result.decision is GateDecision.BLOCKED
            for gate_result in gate_results
        ):
            return IntelligentExecutionStatus.BLOCKED

        return {
            CoordinationStatus.COMPLETED: (
                IntelligentExecutionStatus.COMPLETED
            ),
            CoordinationStatus.FAILED: (
                IntelligentExecutionStatus.FAILED
            ),
            CoordinationStatus.PARTIAL: (
                IntelligentExecutionStatus.PARTIAL
            ),
        }[coordination_status]
__all__ = [
    "CoordinationArtifactCollector",
    "IntelligentOrchestratorService",
]