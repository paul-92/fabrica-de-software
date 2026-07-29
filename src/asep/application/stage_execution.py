"""Execução dos componentes internos de uma etapa de workflow."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from asep.artifacts.manager import ArtifactManager
from asep.execution.models import (
    AgentContext,
    AgentResult,
    AgentResultStatus,
    ArtifactDraft,
    ArtifactReference,
    GateResult,
    StageStatus,
)
from asep.models import RegistrySnapshot
from asep.quality.engine import QualityGateEngine
from asep.runtime.agent_runtime import AgentRuntime


@dataclass(frozen=True, slots=True)
class StageExecutionReport:
    """Resultado da execução interna de uma etapa, sem transições de estado."""

    agent_result: AgentResult
    artifact_references: tuple[ArtifactReference, ...] = ()
    gate_result: GateResult | None = None
    gate_artifact_reference: ArtifactReference | None = None


class StageExecutionService:
    """Executa agente, artefatos e gate sem decidir o estado do workflow."""

    def __init__(
        self,
        agent_runtime: AgentRuntime,
        artifact_manager: ArtifactManager,
        gate_engine: QualityGateEngine,
    ) -> None:
        self._agent_runtime = agent_runtime
        self._artifact_manager = artifact_manager
        self._gate_engine = gate_engine

    def execute(
        self,
        context: AgentContext,
        registry: RegistrySnapshot,
        artifacts_path: Path,
        gate_id: str,
        stage_status: StageStatus,
        logger: logging.Logger,
    ) -> StageExecutionReport:
        result = self._agent_runtime.execute(context, registry, logger)
        if result.status != AgentResultStatus.COMPLETED:
            return StageExecutionReport(agent_result=result)

        references = tuple(
            self._artifact_manager.persist(
                draft,
                artifacts_path,
                run_id=context.run_id,
                project_id=context.project_id,
                stage_id=context.stage_id,
                agent_id=context.agent_id,
            )
            for draft in result.artifacts
        )
        for _reference in references:
            logger.info(
                "Artefato criado.",
                extra={
                    "event_type": "artifact_created",
                    "project_id": context.project_id,
                    "workflow_id": context.workflow_id,
                    "stage_id": context.stage_id,
                    "agent_id": context.agent_id,
                },
            )

        logger.info(
            "Quality gate iniciado.",
            extra={
                "event_type": "gate_started",
                "project_id": context.project_id,
                "workflow_id": context.workflow_id,
                "stage_id": context.stage_id,
            },
        )
        gate = self._gate_engine.evaluate(
            gate_id, result, list(references), stage_status
        )
        gate_reference = self._artifact_manager.persist(
            ArtifactDraft(
                relative_path=f"quality-gates/{context.stage_id}-result.yaml",
                type="yaml",
                content=yaml.safe_dump(
                    gate.model_dump(mode="json"),
                    allow_unicode=True,
                    sort_keys=False,
                ),
            ),
            artifacts_path,
            run_id=context.run_id,
            project_id=context.project_id,
            stage_id=context.stage_id,
            agent_id="quality-gate-engine",
        )
        logger.info(
            f"Quality gate concluído: {gate.decision}.",
            extra={
                "event_type": "gate_completed",
                "project_id": context.project_id,
                "workflow_id": context.workflow_id,
                "stage_id": context.stage_id,
            },
        )
        return StageExecutionReport(
            agent_result=result,
            artifact_references=references,
            gate_result=gate,
            gate_artifact_reference=gate_reference,
        )
