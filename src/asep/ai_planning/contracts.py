"""Contratos públicos do domínio de AI Planning."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from asep.ai_planning.models import EngineeringReflection, RepairProposal
from asep.repair.models import FailureAnalysis, RepairPlan, RepairResult


class RepairProposalPlanner(Protocol):
    """Produz uma proposta estruturada a partir de uma análise de falha."""

    def propose(
        self,
        analysis: FailureAnalysis,
    ) -> RepairProposal:
        ...


class RepairPlanGenerator(Protocol):
    """Transforma uma proposta e conteúdo explícito em plano de reparo."""

    def generate(
        self,
        proposal: RepairProposal,
        *,
        analysis: FailureAnalysis,
        replacement_contents: Mapping[str, str],
        test_paths: tuple[str, ...] = ("tests",),
    ) -> RepairPlan:
        ...


class ReflectionEvaluator(Protocol):
    """Avalia um resultado de reparo sem executar novas ações."""

    def evaluate(
        self,
        result: RepairResult,
    ) -> EngineeringReflection:
        ...


__all__ = [
    "ReflectionEvaluator",
    "RepairPlanGenerator",
    "RepairProposalPlanner",
]
