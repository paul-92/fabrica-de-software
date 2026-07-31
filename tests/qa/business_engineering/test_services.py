"""Testes dos serviços da Business Engineering."""
import pytest

from asep.business_engineering import (
    BlueprintBuilder,
    BusinessDescription,
    RequirementAnalyzer,
    RequirementPriority,
)

def test_requirement_analyzer_creates_requirements_from_sentences() -> None:
    analyzer = RequirementAnalyzer()
    description = BusinessDescription(
        text=(
            "O sistema deve cadastrar clientes. "
            "O gerente deve aprovar pedidos."
        )
    )

    requirements = analyzer.analyze(description)

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
    description = BusinessDescription(
        text="Cadastrar clientes\nEmitir relatórios\nConsultar pedidos"
    )

    requirements = analyzer.analyze(description)

    assert tuple(item.id for item in requirements) == (
        "REQ-001",
        "REQ-002",
        "REQ-003",
    )


def test_requirement_analyzer_shortens_long_titles() -> None:
    analyzer = RequirementAnalyzer()
    description = BusinessDescription(
        text=(
            "O sistema deve permitir que administradores visualizem "
            "relatórios financeiros completos por período"
        )
    )

    requirements = analyzer.analyze(description)
    requirement = requirements[0]

    assert requirement.title.endswith("...")
    assert len(requirement.title) == 63
    assert requirement.description == (
        "O sistema deve permitir que administradores visualizem "
        "relatórios financeiros completos por período"
    )


def test_requirement_analyzer_preserves_description_language() -> None:
    analyzer = RequirementAnalyzer()
    description = BusinessDescription(
        text="Create customers. Generate reports.",
        language="en-US",
        source="api",
    )

    requirements = analyzer.analyze(description)

    assert len(requirements) == 2
    assert requirements[0].description == "Create customers"
    assert requirements[1].description == "Generate reports"

def test_blueprint_builder_creates_project_blueprint() -> None:
    builder = BlueprintBuilder()
    description = BusinessDescription(
        text=(
            "O sistema deve cadastrar clientes. "
            "O gerente deve aprovar pedidos."
        )
    )

    blueprint = builder.build(
        project_name="CRM",
        description=description,
    )

    assert blueprint.project_name == "CRM"
    assert blueprint.description == description.text
    assert len(blueprint.requirements) == 2
    assert blueprint.requirements[0].id == "REQ-001"
    assert blueprint.requirements[1].id == "REQ-002"
    assert blueprint.actors == ()
    assert blueprint.use_cases == ()
    assert blueprint.business_rules == ()
    assert blueprint.entities == ()
    assert blueprint.constraints == ()
    assert blueprint.technology_preferences == ()


def test_blueprint_builder_normalizes_project_name() -> None:
    builder = BlueprintBuilder()
    description = BusinessDescription(
        text="O sistema deve emitir relatórios."
    )

    blueprint = builder.build(
        project_name="  ERP Financeiro  ",
        description=description,
    )

    assert blueprint.project_name == "ERP Financeiro"


def test_blueprint_builder_rejects_blank_project_name() -> None:
    builder = BlueprintBuilder()
    description = BusinessDescription(
        text="O sistema deve cadastrar clientes."
    )

    with pytest.raises(ValueError):
        builder.build(
            project_name="   ",
            description=description,
        )


def test_blueprint_builder_uses_injected_requirement_analyzer() -> None:
    analyzer = RequirementAnalyzer()
    builder = BlueprintBuilder(requirement_analyzer=analyzer)
    description = BusinessDescription(
        text="O sistema deve consultar pedidos."
    )

    blueprint = builder.build(
        project_name="Pedidos",
        description=description,
    )

    assert len(blueprint.requirements) == 1
    assert blueprint.requirements[0].description == (
        "O sistema deve consultar pedidos"
    )    