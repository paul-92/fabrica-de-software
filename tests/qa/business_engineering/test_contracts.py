"""Testes dos contratos da Business Engineering."""

from __future__ import annotations

from datetime import UTC, datetime

from asep.business_engineering import (
    PlanningAdapter,
    ProjectBlueprint,
)
from asep.planning import (
    ExecutionPlan,
    PlanningResult,
    PlanningStatistics,
)


class FakePlanningAdapter(PlanningAdapter):
    """Implementação fake para validar o contrato."""

    def create_execution_plan(
        self,
        blueprint: ProjectBlueprint,
    ) -> PlanningResult:
        return PlanningResult(
            plan=ExecutionPlan(
                plan_id="plan-fake",
                goal=blueprint.description,
                steps=(),
                estimated_cost=0,
                estimated_duration_seconds=0,
                created_at=datetime.now(UTC),
                metadata={
                    "project_name": blueprint.project_name,
                },
            ),
            warnings=(),
            validation_messages=("Plano fake criado.",),
            statistics=PlanningStatistics(
                total_steps=0,
                dependency_count=0,
                maximum_depth=0,
                estimated_cost=0,
                estimated_duration_seconds=0,
                memory_entries_considered=0,
            ),
        )


def test_planning_adapter_contract() -> None:
    adapter = FakePlanningAdapter()

    blueprint = ProjectBlueprint(
        project_name="CRM",
        description="Sistema de CRM",
    )

    result = adapter.create_execution_plan(blueprint)

    assert result.plan.plan_id == "plan-fake"
    assert result.plan.goal == "Sistema de CRM"
    assert result.plan.metadata["project_name"] == "CRM"
    assert result.validation_messages == ("Plano fake criado.",)


def test_planning_adapter_is_polymorphic() -> None:
    adapter: PlanningAdapter = FakePlanningAdapter()

    blueprint = ProjectBlueprint(
        project_name="ERP",
        description="Sistema ERP",
    )

    result = adapter.create_execution_plan(blueprint)

    assert isinstance(result, PlanningResult)
    assert result.plan.goal == "Sistema ERP"
    assert result.statistics.total_steps == 0