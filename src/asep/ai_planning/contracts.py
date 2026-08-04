"""Contratos públicos do domínio de AI Planning."""

from __future__ import annotations

from typing import Protocol

from asep.ai_planning.models import RepairProposal
from asep.repair.models import FailureAnalysis


class RepairProposalPlanner(Protocol):
    """Produz uma proposta estruturada a partir de uma análise de falha."""

    def propose(
        self,
        analysis: FailureAnalysis,
    ) -> RepairProposal:
        ...


__all__ = ["RepairProposalPlanner"]

