from __future__ import annotations

from asep.ai_planning import EngineeringReflection
from asep.learning import LearnedKnowledge, LearningExtractor
from asep.repair import RepairResult, RepairStatus


class ExtractorFake:
    def extract(
        self,
        repair_result,
        reflection,
        *,
        source_execution_id: str,
        source_type: str,
    ) -> LearnedKnowledge:
        return LearnedKnowledge(
            summary=reflection.summary,
            lessons=reflection.lessons,
            recommended_actions=reflection.recommended_actions,
            source_execution_id=source_execution_id,
            source_type=source_type,
            confidence=reflection.confidence,
            metadata={"repair_status": repair_result.status.value},
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
        RepairResult(status=RepairStatus.SUCCEEDED),
        reflection,
        source_execution_id="execution-1",
        source_type="engineering_reflection",
    )

    assert isinstance(result, LearnedKnowledge)
    assert result.summary == reflection.summary
    assert result.source_execution_id == "execution-1"
