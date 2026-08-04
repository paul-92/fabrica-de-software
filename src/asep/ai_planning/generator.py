"""Geração determinística de planos a partir de propostas estruturadas."""

from __future__ import annotations

from collections.abc import Mapping

from asep.ai_planning.models import RepairProposal
from asep.repair.models import (
    FailureAnalysis,
    RepairChange,
    RepairPlan,
)


class DeterministicRepairPlanGenerator:
    """Cria RepairPlan somente com conteúdo de substituição explícito."""

    def generate(
        self,
        proposal: RepairProposal,
        *,
        analysis: FailureAnalysis,
        replacement_contents: Mapping[str, str],
        test_paths: tuple[str, ...] = ("tests",),
    ) -> RepairPlan:
        missing = [
            path
            for path in proposal.candidate_files
            if path not in replacement_contents
            or not isinstance(replacement_contents[path], str)
            or not replacement_contents[path]
        ]

        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                "conteúdo de substituição obrigatório ausente para: "
                f"{joined}"
            )

        reason = "; ".join(proposal.suggested_actions)
        changes = tuple(
            RepairChange(
                path=path,
                content=replacement_contents[path],
                overwrite=True,
                reason=reason,
            )
            for path in proposal.candidate_files
        )

        return RepairPlan(
            analysis=analysis,
            changes=changes,
            test_paths=test_paths,
        )


__all__ = ["DeterministicRepairPlanGenerator"]

