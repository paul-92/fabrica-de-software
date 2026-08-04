from __future__ import annotations

from asep.ai_planning import EngineeringReflection
from asep.learning import LearnedKnowledge, LearningExtractor
from asep.repair import RepairStatus


class ExtractorFake:
    def extract(
        self,
        source,
        *,
        source_execution_id: str,
        source_type: str,
    ) -> LearnedKnowledge:
        return LearnedKnowledge(
            summary=source.summary,
            lessons=source.lessons,
            recommended_actions=source.recommended_actions,
            source_execution_id=source_execution_id,
            source_type=source_type,
            confidence=source.confidence,
        )


def test_learning_extractor_contract_is_structural() -> None:
    extractor: LearningExtractor = ExtractorFake()
    reflection = EngineeringReflection(
        summary="Reparo aprovado.",
        outcome=RepairStatus.SUCCEEDED,
        lessons=("O teste confirmou a correção.",),
        recommended_actions=("Preservar o teste.",),
        should_retry=False,
        confidence=0.9,
    )

    result = extractor.extract(
        reflection,
        source_execution_id="execution-1",
        source_type="engineering_reflection",
    )

    assert isinstance(result, LearnedKnowledge)
    assert result.summary == reflection.summary
    assert result.source_execution_id == "execution-1"

