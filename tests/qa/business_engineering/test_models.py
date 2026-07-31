"""Testes dos modelos de Business Engineering."""

from pydantic import ValidationError
import pytest

from asep.business_engineering.models import (
    Actor,
    ProjectBlueprint,
    Requirement,
    RequirementPriority,
    UseCase,
)

def test_requirement_is_created_with_default_values() -> None:
    requirement = Requirement(
        id="REQ-001",
        title="Cadastrar cliente",
        description="O sistema deve permitir o cadastro de clientes.",
    )

    assert requirement.id == "REQ-001"
    assert requirement.title == "Cadastrar cliente"
    assert requirement.description == (
        "O sistema deve permitir o cadastro de clientes."
    )
    assert requirement.priority is RequirementPriority.MEDIUM
    assert requirement.functional is True


def test_requirement_accepts_explicit_priority() -> None:
    requirement = Requirement(
        id="REQ-002",
        title="Proteger dados",
        description="Os dados sensíveis devem ser protegidos.",
        priority=RequirementPriority.CRITICAL,
        functional=False,
    )

    assert requirement.priority is RequirementPriority.CRITICAL
    assert requirement.functional is False


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("id", ""),
        ("title", "   "),
        ("description", "\t"),
    ],
)
def test_requirement_rejects_blank_required_text(
    field_name: str,
    field_value: str,
) -> None:
    data = {
        "id": "REQ-003",
        "title": "Emitir relatório",
        "description": "O sistema deve emitir relatórios.",
    }
    data[field_name] = field_value

    with pytest.raises(ValidationError):
        Requirement(**data)


def test_requirement_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Requirement(
            id="REQ-004",
            title="Consultar cliente",
            description="O sistema deve consultar clientes.",
            unknown_field="valor",
        )


def test_requirement_is_immutable() -> None:
    requirement = Requirement(
        id="REQ-005",
        title="Excluir cliente",
        description="O sistema deve permitir excluir clientes.",
    )

    with pytest.raises(ValidationError):
        requirement.title = "Novo título"

def test_actor_is_created() -> None:
    actor = Actor(
        id="ACT-001",
        name="Gerente",
        description="Responsável por aprovar pedidos.",
    )

    assert actor.id == "ACT-001"
    assert actor.name == "Gerente"
    assert actor.description == "Responsável por aprovar pedidos."


def test_actor_accepts_optional_description() -> None:
    actor = Actor(
        id="ACT-002",
        name="Cliente",
    )

    assert actor.description is None


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("id", ""),
        ("name", "   "),
    ],
)
def test_actor_rejects_blank_required_text(
    field_name: str,
    field_value: str,
) -> None:
    data = {
        "id": "ACT-003",
        "name": "Administrador",
    }
    data[field_name] = field_value

    with pytest.raises(ValidationError):
        Actor(**data)


def test_actor_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Actor(
            id="ACT-004",
            name="Vendedor",
            role="sales",
        )


def test_actor_is_immutable() -> None:
    actor = Actor(
        id="ACT-005",
        name="Usuário",
    )

    with pytest.raises(ValidationError):
        actor.name = "Administrador"        

def test_use_case_is_created() -> None:
    use_case = UseCase(
        id="UC-001",
        name="Realizar pedido",
        description="Permite que o cliente realize um pedido.",
        primary_actor_id="ACT-001",
        requirement_ids=("REQ-001", "REQ-002"),
    )

    assert use_case.id == "UC-001"
    assert use_case.name == "Realizar pedido"
    assert use_case.description == (
        "Permite que o cliente realize um pedido."
    )
    assert use_case.primary_actor_id == "ACT-001"
    assert use_case.requirement_ids == ("REQ-001", "REQ-002")


def test_use_case_accepts_empty_requirement_ids() -> None:
    use_case = UseCase(
        id="UC-002",
        name="Consultar pedido",
        description="Permite consultar um pedido existente.",
        primary_actor_id="ACT-002",
    )

    assert use_case.requirement_ids == ()


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("id", ""),
        ("name", "   "),
        ("description", "\t"),
        ("primary_actor_id", "\n"),
    ],
)
def test_use_case_rejects_blank_required_text(
    field_name: str,
    field_value: str,
) -> None:
    data = {
        "id": "UC-003",
        "name": "Cancelar pedido",
        "description": "Permite cancelar um pedido.",
        "primary_actor_id": "ACT-003",
    }
    data[field_name] = field_value

    with pytest.raises(ValidationError):
        UseCase(**data)


def test_use_case_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        UseCase(
            id="UC-004",
            name="Aprovar pedido",
            description="Permite aprovar um pedido.",
            primary_actor_id="ACT-004",
            secondary_actor_id="ACT-005",
        )


def test_use_case_is_immutable() -> None:
    use_case = UseCase(
        id="UC-005",
        name="Excluir pedido",
        description="Permite excluir um pedido.",
        primary_actor_id="ACT-005",
    )

    with pytest.raises(ValidationError):
        use_case.name = "Arquivar pedido"

def test_project_blueprint_is_created() -> None:
    requirement = Requirement(
        id="REQ-001",
        title="Cadastrar cliente",
        description="O sistema deve cadastrar clientes.",
    )

    actor = Actor(
        id="ACT-001",
        name="Administrador",
    )

    use_case = UseCase(
        id="UC-001",
        name="Cadastrar cliente",
        description="Permite cadastrar clientes.",
        primary_actor_id="ACT-001",
        requirement_ids=("REQ-001",),
    )

    blueprint = ProjectBlueprint(
        project_name="CRM",
        description="Sistema de CRM.",
        requirements=(requirement,),
        actors=(actor,),
        use_cases=(use_case,),
    )

    assert blueprint.project_name == "CRM"
    assert blueprint.description == "Sistema de CRM."
    assert len(blueprint.requirements) == 1
    assert len(blueprint.actors) == 1
    assert len(blueprint.use_cases) == 1


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("project_name", ""),
        ("description", "   "),
    ],
)
def test_project_blueprint_rejects_blank_required_text(
    field_name: str,
    field_value: str,
) -> None:
    data = {
        "project_name": "ERP",
        "description": "Sistema ERP.",
    }

    data[field_name] = field_value

    with pytest.raises(ValidationError):
        ProjectBlueprint(**data)


def test_project_blueprint_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProjectBlueprint(
            project_name="Financeiro",
            description="Sistema Financeiro.",
            version="1.0",
        )


def test_project_blueprint_is_immutable() -> None:
    blueprint = ProjectBlueprint(
        project_name="Loja Virtual",
        description="Sistema de e-commerce.",
    )

    with pytest.raises(ValidationError):
        blueprint.project_name = "Marketplace"        