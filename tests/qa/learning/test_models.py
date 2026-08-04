from __future__ import annotations

import pytest
from pydantic import ValidationError

from asep.learning import LearnedKnowledge


def knowledge(**changes) -> LearnedKnowledge:
    values = {
        "summary": "A validação deve acompanhar a correção.",
        "lessons": ("Uma mudança sem teste não comprova reparo.",),
        "recommended_actions": ("Executar o teste afetado.",),
        "source_execution_id": "repair-42",
        "source_type": "engineering_reflection",
        "confidence": 0.85,
        "metadata": {"project": "calculator"},
    }
    values.update(changes)
    return LearnedKnowledge(**values)


def test_learned_knowledge_preserves_structured_data() -> None:
    result = knowledge()

    assert result.source_execution_id == "repair-42"
    assert result.lessons == ("Uma mudança sem teste não comprova reparo.",)
    assert result.metadata["project"] == "calculator"


def test_learned_knowledge_is_immutable_and_strict() -> None:
    result = knowledge()

    with pytest.raises(ValidationError):
        result.confidence = 0.1

    with pytest.raises(ValidationError):
        LearnedKnowledge(
            summary=result.summary,
            lessons=result.lessons,
            recommended_actions=result.recommended_actions,
            source_execution_id=result.source_execution_id,
            source_type=result.source_type,
            confidence=result.confidence,
            metadata={"project": "calculator"},
            unexpected=True,
        )


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_learned_knowledge_validates_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        knowledge(confidence=confidence)
