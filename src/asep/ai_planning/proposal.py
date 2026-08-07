"""Planejamento determinístico de propostas estruturadas de reparo."""

from __future__ import annotations

from asep.ai_planning.models import RepairProposal
from asep.repair.models import FailureAnalysis


class DeterministicRepairProposalPlanner:
    """Deriva uma proposta exclusivamente dos fatos da análise de falha."""

    def propose(self, analysis: FailureAnalysis) -> RepairProposal:
        candidate_files = tuple(
            sorted(
                {
                    path.strip()
                    for path in analysis.affected_paths
                    if path.strip()
                }
            )
        )
        if not candidate_files:
            raise ValueError(
                "affected_paths deve identificar ao menos um arquivo para reparo"
            )

        evidence = (
            analysis.probable_cause
            or analysis.failure_output
            or analysis.summary
        )
        confidence = (
            0.9
            if analysis.probable_cause
            else 0.75
            if analysis.failure_output
            else 0.6
        )
        actions = tuple(
            f"Aplicar alteração controlada ao arquivo afetado {path}."
            for path in candidate_files
        )
        return RepairProposal(
            summary=analysis.summary,
            reasoning=f"Evidência disponível na análise: {evidence}",
            candidate_files=candidate_files,
            suggested_actions=actions,
            confidence=confidence,
        )


__all__ = ["DeterministicRepairProposalPlanner"]
