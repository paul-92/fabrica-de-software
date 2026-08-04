from __future__ import annotations

from pathlib import Path

import pytest

from asep.ai_planning import (
    DeterministicRepairPlanGenerator,
    RepairPlanGenerator,
    RepairProposal,
)
from asep.repair import FailureAnalysis, RepairPlan


def proposal(*candidate_files: str) -> RepairProposal:
    return RepairProposal(
        summary="A soma está incorreta.",
        reasoning="O operador usado não corresponde ao comportamento esperado.",
        candidate_files=candidate_files,
        suggested_actions=(
            "Revisar a operação aritmética.",
            "Executar os testes da calculadora.",
        ),
        confidence=0.95,
    )


def analysis() -> FailureAnalysis:
    return FailureAnalysis(
        summary="Teste da soma falhou.",
        affected_paths=("calculator.py",),
    )


def test_generator_transforms_proposal_into_repair_plan() -> None:
    generator = DeterministicRepairPlanGenerator()

    result = generator.generate(
        proposal("calculator.py"),
        analysis=analysis(),
        replacement_contents={
            "calculator.py": "def add(a, b):\n    return a + b\n",
        },
        test_paths=("tests/test_calculator.py",),
    )

    assert isinstance(result, RepairPlan)
    assert result.analysis == analysis()
    assert result.changes[0].path == "calculator.py"
    assert result.changes[0].content.endswith("return a + b\n")
    assert result.test_paths == ("tests/test_calculator.py",)


def test_generator_creates_one_change_for_each_candidate_file() -> None:
    result = DeterministicRepairPlanGenerator().generate(
        proposal("calculator.py", "tests/test_calculator.py"),
        analysis=analysis(),
        replacement_contents={
            "calculator.py": "implementation",
            "tests/test_calculator.py": "tests",
        },
    )

    assert tuple(change.path for change in result.changes) == (
        "calculator.py",
        "tests/test_calculator.py",
    )


def test_generator_preserves_all_suggested_actions_as_change_reason() -> None:
    source = proposal("calculator.py")
    result = DeterministicRepairPlanGenerator().generate(
        source,
        analysis=analysis(),
        replacement_contents={"calculator.py": "replacement"},
    )

    for action in source.suggested_actions:
        assert action in result.changes[0].reason


@pytest.mark.parametrize("contents", [{}, {"calculator.py": ""}])
def test_generator_rejects_missing_required_content(contents) -> None:
    with pytest.raises(ValueError, match="conteúdo de substituição"):
        DeterministicRepairPlanGenerator().generate(
            proposal("calculator.py"),
            analysis=analysis(),
            replacement_contents=contents,
        )


def test_generator_satisfies_public_protocol() -> None:
    generator: RepairPlanGenerator = DeterministicRepairPlanGenerator()

    result = generator.generate(
        proposal("calculator.py"),
        analysis=analysis(),
        replacement_contents={"calculator.py": "replacement"},
    )

    assert isinstance(result, RepairPlan)


def test_generator_has_no_effectful_dependencies() -> None:
    source = Path("src/asep/ai_planning/generator.py").read_text(
        encoding="utf-8"
    )

    assert "write_text" not in source
    assert "subprocess" not in source
    assert "Tool" not in source
    assert "DeveloperAgent" not in source

