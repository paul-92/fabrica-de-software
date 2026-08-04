from __future__ import annotations

import pytest
from pydantic import ValidationError

from asep.ai_planning.models import RepairProposal


def valid_proposal() -> RepairProposal:
    return RepairProposal(
        summary="A operação de soma produz resultado incorreto.",
        reasoning="A falha aponta para o módulo da calculadora.",
        candidate_files=("calculator.py",),
        suggested_actions=(
            "Revisar a operação aritmética usada pela função add.",
            "Validar novamente os testes da calculadora.",
        ),
        confidence=0.9,
    )


def test_repair_proposal_preserves_structured_information() -> None:
    proposal = valid_proposal()

    assert proposal.summary.startswith("A operação")
    assert proposal.candidate_files == ("calculator.py",)
    assert len(proposal.suggested_actions) == 2
    assert proposal.confidence == 0.9
    assert "content" not in type(proposal).model_fields
    assert "code" not in type(proposal).model_fields


def test_repair_proposal_is_immutable_and_strict() -> None:
    proposal = valid_proposal()

    with pytest.raises(ValidationError):
        proposal.confidence = 0.2

    with pytest.raises(ValidationError):
        RepairProposal(
            **proposal.model_dump(),
            unexpected="value",
        )


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_repair_proposal_rejects_confidence_outside_range(
    confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        RepairProposal(
            **{
                **valid_proposal().model_dump(),
                "confidence": confidence,
            }
        )


def test_repair_proposal_rejects_blank_structured_values() -> None:
    with pytest.raises(ValidationError):
        RepairProposal(
            summary=" ",
            reasoning="Explicação.",
            candidate_files=("calculator.py",),
            suggested_actions=("Revisar operação.",),
            confidence=0.5,
        )

    with pytest.raises(ValidationError):
        RepairProposal(
            summary="Falha.",
            reasoning="Explicação.",
            candidate_files=("",),
            suggested_actions=("Revisar operação.",),
            confidence=0.5,
        )

