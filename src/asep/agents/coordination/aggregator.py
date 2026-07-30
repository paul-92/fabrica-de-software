"""Agregação determinística de resultados individuais."""

from time import perf_counter
from typing import Callable

from asep.agents.coordination.exceptions import ResultAggregationError
from asep.agents.coordination.models import (
    AgentAssignment,
    AssignmentStatus,
    CoordinationContext,
    CoordinationResult,
    CoordinationStatistics,
    CoordinationStatus,
)
from asep.agents.runtime_models import AgentExecutionStatus

Timer = Callable[[], float]


class DeterministicResultAggregator:
    def __init__(self, timer: Timer | None = None) -> None:
        self._timer = timer or perf_counter

    def aggregate(
        self,
        context: CoordinationContext,
        assignments: tuple[AgentAssignment, ...],
    ) -> CoordinationResult:
        started = self._timer()
        results_by_step = {
            result.metadata.get("plan_step_id"): result
            for result in context.partial_results
        }
        if len(results_by_step) != len(context.partial_results):
            raise ResultAggregationError(
                "Resultados duplicados ou sem plan_step_id."
            )
        ordered_results = tuple(
            results_by_step[item.plan_step_id]
            for item in assignments
            if item.plan_step_id in results_by_step
        )
        failures = sum(
            result.status is not AgentExecutionStatus.SUCCEEDED
            for result in ordered_results
        ) + (len(assignments) - len(ordered_results))
        status = (
            CoordinationStatus.COMPLETED
            if failures == 0
            else CoordinationStatus.FAILED
            if not ordered_results
            else CoordinationStatus.PARTIAL
        )
        duration = max(0.0, self._timer() - started)
        completed = sum(
            item.status is AssignmentStatus.COMPLETED
            for item in assignments
        )
        run_id = str(
            context.metadata.get(
                "run_id", context.execution_plan.plan_id
            )
        )
        return CoordinationResult(
            plan_id=context.execution_plan.plan_id,
            run_id=run_id,
            status=status,
            assignments=assignments,
            results=ordered_results,
            output={
                str(result.metadata["plan_step_id"]): result.model_dump(
                    mode="json"
                )
                for result in ordered_results
            },
            statistics=CoordinationStatistics(
                assignments_total=len(assignments),
                completed_total=completed,
                failed_total=failures,
                agents_used=len(
                    {item.agent_id.value for item in assignments}
                ),
                duration_seconds=0,
                aggregation_duration_seconds=duration,
            ),
        )


__all__ = ["DeterministicResultAggregator"]
