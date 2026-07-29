"""Quality Gate Engine limitado a critérios verificáveis da Sprint 2."""

from __future__ import annotations

from datetime import UTC, datetime

from asep.execution.models import (
    AgentResult,
    AgentResultStatus,
    ArtifactReference,
    GateDecision,
    GateResult,
    StageStatus,
)


class QualityGateEngine:
    def evaluate(
        self,
        gate_id: str,
        result: AgentResult,
        artifacts: list[ArtifactReference],
        stage_status: StageStatus,
    ) -> GateResult:
        checks = {
            "resultado do agente é válido": result.status
            == AgentResultStatus.COMPLETED,
            "artefato obrigatório existe": bool(artifacts),
            "campos obrigatórios estão preenchidos": all(
                (result.run_id, result.stage_id, result.agent_id)
            ),
            "não existem erros críticos": not result.errors,
            "estado da etapa é compatível": stage_status == StageStatus.RUNNING,
        }
        satisfied = [name for name, passed in checks.items() if passed]
        unsatisfied = [name for name, passed in checks.items() if not passed]
        if unsatisfied:
            decision = GateDecision.BLOCKED
        elif result.warnings:
            decision = GateDecision.APPROVED_WITH_PENDING
        else:
            decision = GateDecision.APPROVED
        return GateResult(
            gate_id=gate_id,
            run_id=result.run_id,
            stage_id=result.stage_id,
            decision=decision,
            satisfied_criteria=satisfied,
            unsatisfied_criteria=unsatisfied,
            evaluated_at=datetime.now(UTC),
        )
