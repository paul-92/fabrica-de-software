"""Testes dos serviços da Business Engineering."""

import pytest

from asep.business_engineering import (
    RequirementAnalyzer,
    RequirementPriority,
)


def test_requirement_analyzer_creates_requirements_from_sentences() -> None:
    analyzer = RequirementAnalyzer()

    requirements = analyzer.analyze(
        (
            "O sistema deve cadastrar clientes. "
            "O gerente deve aprovar pedidos."
        )
    )

    assert len(requirements) == 2

    assert requirements[0].id == "REQ-001"
    assert requirements[0].title == "O sistema deve cadastrar clientes"
    assert requirements[0].description == (
        "O sistema deve cadastrar clientes"
    )
    assert requirements[0].priority is RequirementPriority.MEDIUM
    assert requirements[0].functional is True

    assert requirements[1].id == "REQ-002"
    assert requirements[1].title == "O gerente deve aprovar pedidos"
    assert requirements[1].description == (
        "O gerente deve aprovar pedidos"
    )


def test_requirement_analyzer_accepts_line_breaks() -> None:
    analyzer = RequirementAnalyzer()

    requirements = analyzer.analyze(
        "Cadastrar clientes\nEmitir relatórios\nConsultar pedidos"
    )

    assert tuple(item.id for item in requirements) == (
        "REQ-001",
        "REQ-002",
        "REQ-003",
    )


@pytest.mark.parametrize(
    "description",
    [
        "",
        "   ",
        "\n\t",
        "...!!!???",
    ],
)
def test_requirement_analyzer_rejects_invalid_description(
    description: str,
) -> None:
    analyzer = RequirementAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze(description)


def test_requirement_analyzer_shortens_long_titles() -> None:
    analyzer = RequirementAnalyzer()

    requirements = analyzer.analyze(
        (
            "O sistema deve permitir que administradores visualizem "
            "relatórios financeiros completos por período"
        )
    )

    requirement = requirements[0]

    assert requirement.title.endswith("...")
    assert len(requirement.title) == 63
    assert requirement.description == (
        "O sistema deve permitir que administradores visualizem "
        "relatórios financeiros completos por período"
    )