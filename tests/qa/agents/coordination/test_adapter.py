"""Testes do AgentCoordinatorAdapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from asep.agents.coordination import (
    AgentCoordinatorAdapter,
    CoordinationContext,
    CoordinationResult,
    CoordinationStatistics,
    CoordinationStatus,
)
from asep.business_engineering import (
    BlueprintBuilder,
    BusinessDescription,
    PlanningEngineAdapter,
)
from asep.planning import (
    ExecutionPlan,
    PlanningResult,
    PlanningStatistics,
)


class SpyCoordinator:
    """Coordinator de teste que registra o contexto recebido."""

    def __init__(self) -> None:
        self.received_context: CoordinationContext | None = None

    def coordinate(
        self,
        context: CoordinationContext,
    ) -> CoordinationResult:
        self.received_context = context

        return CoordinationResult(
            plan_id=context.execution_plan.plan_id,
            run_id="run-test",
            status=CoordinationStatus.COMPLETED,
            assignments=(),
            results=(),
            output={},
            statistics=CoordinationStatistics(
                assignments_total=0,
                completed_total=0,
                failed_total=0,
                agents_used=0,
                duration_seconds=0,
                aggregation_duration_seconds=0,
            ),
        )


class SpyPlanningEngine:
    """Planning Engine fake."""

    def plan(self, request):
        return PlanningResult(
            plan=ExecutionPlan(
                plan_id="plan-001",
                goal=request.goal,
                steps=(),
                estimated_cost=0,
                estimated_duration_seconds=0,
                created_at=datetime.now(UTC),
                metadata={},
            ),
            warnings=("warning",),
            validation_messages=("validated",),
            statistics=PlanningStatistics(
                total_steps=0,
                dependency_count=0,
                maximum_depth=0,
                estimated_cost=0,
                estimated_duration_seconds=0,
                memory_entries_considered=0,
            ),
        )


def test_agent_coordinator_adapter_creates_context() -> None:
    blueprint = BlueprintBuilder().build(
        project_name="CRM",
        description=BusinessDescription(
            text="Cadastrar clientes.",
        ),
    )

    planning_result = PlanningEngineAdapter(
        planning_engine=cast(object, SpyPlanningEngine()),
    ).create_execution_plan(blueprint)

    coordinator = SpyCoordinator()

    adapter = AgentCoordinatorAdapter(
        coordinator=cast(object, coordinator),
    )

    result = adapter.coordinate(planning_result)

    context = coordinator.received_context

    assert context is not None
    assert context.execution_plan.plan_id == "plan-001"
    assert context.metadata["plan_id"] == "plan-001"
    #assert context.metadata["planning_warnings"] == ("warning",)
    assert context.metadata["planning_warnings"] == ["warning"]
    assert context.metadata["planning_validation_messages"] == [
    "validated"
]

    assert result.plan_id == "plan-001"
    assert result.status is CoordinationStatus.COMPLETED
    