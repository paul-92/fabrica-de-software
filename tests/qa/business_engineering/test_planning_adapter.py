"""Testes do adaptador entre Business Engineering e Planning."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from asep.business_engineering import (
    BusinessDescription,
    BlueprintBuilder,
    PlanningEngineAdapter,
)
from asep.planning import (
    ExecutionPlan,
    PlanningRequest,
    PlanningResult,
    PlanningStatistics,
)


class SpyPlanningEngine:
    """Planning Engine de teste que registra a solicitação recebida."""

    def __init__(self) -> None:
        self.received_request: PlanningRequest | None = None

    def plan(self, request: PlanningRequest) -> PlanningResult:
        self.received_request = request

        return PlanningResult(
            plan=ExecutionPlan(
                plan_id="plan-test",
                goal=request.goal,
                steps=(),
                estimated_cost=0,
                estimated_duration_seconds=0,
                created_at=datetime.now(UTC),
            ),
            warnings=(),
            validation_messages=("Plano de teste criado.",),
            statistics=PlanningStatistics(
                total_steps=0,
                dependency_count=0,
                maximum_depth=0,
                estimated_cost=0,
                estimated_duration_seconds=0,
                memory_entries_considered=0,
            ),
        )


def test_planning_engine_adapter_builds_planning_request() -> None:
    description = BusinessDescription(
        text=(
            "O sistema deve cadastrar clientes. "
            "O sistema deve emitir relatórios."
        )
    )
    blueprint = BlueprintBuilder().build(
        project_name="CRM",
        description=description,
    )
    engine = SpyPlanningEngine()
    adapter = PlanningEngineAdapter(
        planning_engine=cast(object, engine),
    )

    adapter.create_execution_plan(blueprint)

    request = engine.received_request

    assert request is not None
    assert request.goal == blueprint.description
    assert request.context.objective == "CRM"

    steps = request.context.workflow["steps"]

    assert len(steps) == 2
    assert steps[0] == {
        "id": "REQ-001",
        "description": "O sistema deve cadastrar clientes",
        "required_capability": "implement_requirement",
    }
    assert steps[1] == {
        "id": "REQ-002",
        "description": "O sistema deve emitir relatórios",
        "required_capability": "implement_requirement",
    }


def test_planning_engine_adapter_transfers_context() -> None:
    description = BusinessDescription(
        text="O sistema deve armazenar dados de clientes."
    )
    blueprint = BlueprintBuilder().build(
        project_name="Cadastro",
        description=description,
    )
    engine = SpyPlanningEngine()
    adapter = PlanningEngineAdapter(
        planning_engine=cast(object, engine),
    )

    adapter.create_execution_plan(blueprint)

    request = engine.received_request

    assert request is not None
    assert request.context.constraints == ()
    assert request.context.metadata["project_name"] == "Cadastro"
    assert request.metadata["requirement_count"] == 1


def test_planning_engine_adapter_returns_planning_result() -> None:
    description = BusinessDescription(
        text="O sistema deve consultar pedidos."
    )
    blueprint = BlueprintBuilder().build(
        project_name="Pedidos",
        description=description,
    )
    engine = SpyPlanningEngine()
    adapter = PlanningEngineAdapter(
        planning_engine=cast(object, engine),
    )

    result = adapter.create_execution_plan(blueprint)

    assert result.plan.plan_id == "plan-test"
    assert result.plan.goal == blueprint.description
    assert result.validation_messages == ("Plano de teste criado.",)