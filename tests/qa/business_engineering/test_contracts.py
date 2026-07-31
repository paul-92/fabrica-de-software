"""Testes dos contratos da Business Engineering."""

from __future__ import annotations

from asep.business_engineering import (
    PlanningAdapter,
    ProjectBlueprint,
)


class FakePlanningAdapter(PlanningAdapter):
    """Implementação fake para validar o contrato."""

    def create_execution_plan(
        self,
        blueprint: ProjectBlueprint,
    ) -> object:
        return {
            "project": blueprint.project_name,
            "requirements": len(blueprint.requirements),
        }


def test_planning_adapter_contract() -> None:
    adapter = FakePlanningAdapter()

    blueprint = ProjectBlueprint(
        project_name="CRM",
        description="Sistema de CRM",
    )

    result = adapter.create_execution_plan(blueprint)

    assert result == {
        "project": "CRM",
        "requirements": 0,
    }


def test_planning_adapter_is_polymorphic() -> None:
    adapter: PlanningAdapter = FakePlanningAdapter()

    blueprint = ProjectBlueprint(
        project_name="ERP",
        description="Sistema ERP",
    )

    result = adapter.create_execution_plan(blueprint)

    assert result["project"] == "ERP"