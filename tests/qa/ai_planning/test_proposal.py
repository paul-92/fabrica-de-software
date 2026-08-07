from pathlib import Path

import pytest

from asep.ai_planning import DeterministicRepairProposalPlanner
from asep.repair import FailureAnalysis


def test_proposal_is_derived_only_from_failure_analysis() -> None:
    analysis = FailureAnalysis(
        summary="Falha na soma.",
        failure_output="assert 4 == 5",
        affected_paths=("z.py", "a.py", "z.py"),
        probable_cause="Operador incorreto.",
    )

    proposal = DeterministicRepairProposalPlanner().propose(analysis)

    assert proposal.summary == analysis.summary
    assert proposal.reasoning == (
        "Evidência disponível na análise: Operador incorreto."
    )
    assert proposal.candidate_files == ("a.py", "z.py")
    assert proposal.suggested_actions == (
        "Aplicar alteração controlada ao arquivo afetado a.py.",
        "Aplicar alteração controlada ao arquivo afetado z.py.",
    )
    assert proposal.confidence == 0.9


@pytest.mark.parametrize(
    ("analysis", "confidence"),
    [
        (FailureAnalysis(summary="Falha", affected_paths=("a.py",)), 0.6),
        (
            FailureAnalysis(
                summary="Falha",
                failure_output="trace",
                affected_paths=("a.py",),
            ),
            0.75,
        ),
    ],
)
def test_confidence_is_deterministic(
    analysis: FailureAnalysis,
    confidence: float,
) -> None:
    assert (
        DeterministicRepairProposalPlanner().propose(analysis).confidence
        == confidence
    )


def test_missing_affected_paths_fails_explicitly() -> None:
    with pytest.raises(ValueError, match="affected_paths"):
        DeterministicRepairProposalPlanner().propose(
            FailureAnalysis(summary="Falha sem arquivo identificado.")
        )


def test_planner_performs_no_filesystem_io(tmp_path: Path) -> None:
    before = tuple(tmp_path.iterdir())
    DeterministicRepairProposalPlanner().propose(
        FailureAnalysis(summary="Falha", affected_paths=("missing.py",))
    )
    assert tuple(tmp_path.iterdir()) == before
