from __future__ import annotations

from asep.ai_planning.contracts import RepairProposalPlanner
from asep.ai_planning.models import RepairProposal
from asep.repair.models import FailureAnalysis


class DeterministicProposalPlanner:
    def propose(self, analysis: FailureAnalysis) -> RepairProposal:
        return RepairProposal(
            summary=analysis.summary,
            reasoning=analysis.probable_cause or "Causa não identificada.",
            candidate_files=analysis.affected_paths or ("<unknown>",),
            suggested_actions=("Inspecionar os arquivos candidatos.",),
            confidence=0.5,
        )


def test_repair_proposal_planner_contract_is_structural() -> None:
    planner: RepairProposalPlanner = DeterministicProposalPlanner()
    analysis = FailureAnalysis(
        summary="Teste falhou.",
        affected_paths=("calculator.py",),
        probable_cause="Operação incorreta.",
    )

    proposal = planner.propose(analysis)

    assert isinstance(proposal, RepairProposal)
    assert proposal.summary == analysis.summary
    assert proposal.candidate_files == analysis.affected_paths


def test_contract_can_produce_identical_proposals_deterministically() -> None:
    planner = DeterministicProposalPlanner()
    analysis = FailureAnalysis(summary="Falha reproduzível.")

    assert planner.propose(analysis) == planner.propose(analysis)

