from __future__ import annotations

import pytest

from asep.ai_planning import EngineeringReflection
from asep.learning import DeterministicLearningExtractor
from asep.repair import RepairResult, RepairStatus


@pytest.mark.parametrize(
    ("status", "should_retry"),
    [
        (RepairStatus.SUCCEEDED, False),
        (RepairStatus.FAILED, True),
        (RepairStatus.EXHAUSTED, False),
    ],
)
def test_extractor_preserves_reflection_for_each_outcome(
    status: RepairStatus,
    should_retry: bool,
) -> None:
    repair_result = RepairResult(
        status=status,
        messages=("Resultado observado.",),
    )
    reflection = EngineeringReflection(
        summary=f"Resultado {status.value}.",
        outcome=status,
        lessons=("Lição comprovada.",),
        recommended_actions=("Revisar conscientemente.",),
        should_retry=should_retry,
        confidence=0.75,
    )

    knowledge = DeterministicLearningExtractor().extract(
        repair_result,
        reflection,
        source_execution_id="execution-explicit",
        source_type="repair_reflection",
    )

    assert knowledge.summary == reflection.summary
    assert knowledge.lessons == reflection.lessons
    assert knowledge.recommended_actions == reflection.recommended_actions
    assert knowledge.confidence == 0.75
    assert knowledge.source_execution_id == "execution-explicit"
    assert knowledge.source_type == "repair_reflection"
    assert knowledge.metadata["repair_status"] == status.value
    assert knowledge.metadata["should_retry"] is should_retry

