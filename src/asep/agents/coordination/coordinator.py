"""Coordenação sequencial de ExecutionPlan por contratos de agentes."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter

from asep.agents.contracts import AgentCapability
from asep.agents.coordination.aggregator import (
    DeterministicResultAggregator,
)
from asep.agents.coordination.contracts import (
    AgentCapabilityResolver,
    AgentExecutionResultAggregator,
)
from asep.agents.coordination.metrics import CoordinationMetricsRecorder
from asep.agents.coordination.models import (
    AgentAssignment,
    AssignmentStatus,
    CoordinationContext,
    CoordinationPolicy,
    CoordinationResult,
)
from asep.agents.coordination.queue import AgentExecutionQueue
from asep.agents.coordination.resolver import (
    RegistryAgentCapabilityResolver,
)
from asep.agents.coordination.validator import CoordinationValidator
from asep.agents.registry import AgentRegistry
from asep.agents.runtime import AgentRuntime
from asep.agents.runtime_models import (
    AgentExecutionRequest,
    AgentExecutionStatus,
)
from asep.timeline import TimelineEventType, TimelineRecorder

Clock = Callable[[], datetime]
Timer = Callable[[], float]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class _NullMetrics:
    def completed(
        self,
        *,
        assignments: int,
        duration_seconds: float,
        aggregation_duration_seconds: float,
    ) -> None:
        del assignments, duration_seconds, aggregation_duration_seconds

    def failed(self, *, duration_seconds: float) -> None:
        del duration_seconds


class AgentCoordinator:
    def __init__(
        self,
        registry: AgentRegistry,
        runtime: AgentRuntime,
        *,
        timeline: TimelineRecorder,
        policy: CoordinationPolicy | None = None,
        resolver: AgentCapabilityResolver | None = None,
        queue: AgentExecutionQueue | None = None,
        aggregator: AgentExecutionResultAggregator | None = None,
        validator: CoordinationValidator | None = None,
        metrics: CoordinationMetricsRecorder | None = None,
        clock: Clock | None = None,
        timer: Timer | None = None,
    ) -> None:
        self._registry = registry
        self._runtime = runtime
        self._timeline = timeline
        self._policy = policy or CoordinationPolicy()
        self._resolver = resolver or RegistryAgentCapabilityResolver(
            registry,
            self._policy.selection,
            allow_fallback=self._policy.allow_fallback,
        )
        self._queue = queue or AgentExecutionQueue()
        self._aggregator = aggregator or DeterministicResultAggregator()
        self._validator = validator or CoordinationValidator()
        self._metrics = metrics or _NullMetrics()
        self._clock = clock or _utc_now
        self._timer = timer or perf_counter

    def coordinate(
        self, context: CoordinationContext
    ) -> CoordinationResult:
        started = self._timer()
        run_id = str(
            context.metadata.get(
                "run_id", context.execution_plan.plan_id
            )
        )
        self._record(run_id, TimelineEventType.COORDINATION_STARTED)
        try:
            self._validator.validate_context(context, self._policy)
            assignments = self._assign(context, run_id)
            self._validator.validate_assignments(
                context, assignments, self._registry, self._policy
            )
            ordered = self._queue.order(
                context.execution_plan, assignments, self._policy
            )
            completed, results = self._execute(
                context, ordered, run_id
            )
            aggregation_context = context.model_copy(
                update={
                    "assignments": completed,
                    "partial_results": results,
                }
            )
            result = self._aggregator.aggregate(
                aggregation_context, completed
            )
        except Exception as exc:
            duration = max(0.0, self._timer() - started)
            self._metrics.failed(duration_seconds=duration)
            self._timeline.record(
                run_id,
                TimelineEventType.COORDINATION_FAILED,
                message=TimelineEventType.COORDINATION_FAILED.value,
                metadata={"error_type": type(exc).__name__},
            )
            raise

        duration = max(0.0, self._timer() - started)
        statistics = result.statistics.model_copy(
            update={"duration_seconds": duration}
        )
        result = result.model_copy(update={"statistics": statistics})
        self._metrics.completed(
            assignments=len(completed),
            duration_seconds=duration,
            aggregation_duration_seconds=(
                statistics.aggregation_duration_seconds
            ),
        )
        self._record(
            run_id,
            TimelineEventType.COORDINATION_COMPLETED,
            {
                "plan_id": result.plan_id,
                "status": result.status.value,
                "assignments": len(completed),
            },
        )
        return result

    def _assign(
        self, context: CoordinationContext, run_id: str
    ) -> tuple[AgentAssignment, ...]:
        assignments = []
        for step in context.execution_plan.steps:
            agent_id = self._resolver.resolve(step)
            self._record(
                run_id,
                TimelineEventType.AGENT_SELECTED,
                {
                    "plan_step_id": step.step_id,
                    "agent_id": agent_id.value,
                },
            )
            assignment = AgentAssignment(
                assignment_id=self._assignment_id(
                    context.execution_plan.plan_id,
                    step.step_id,
                    agent_id.value,
                ),
                plan_step_id=step.step_id,
                agent_id=agent_id,
                required_capability=step.required_capability,
                priority=step.priority,
                created_at=self._clock(),
                metadata={"plan_id": context.execution_plan.plan_id},
            )
            assignments.append(assignment)
            self._record(
                run_id,
                TimelineEventType.ASSIGNMENT_CREATED,
                {
                    "assignment_id": assignment.assignment_id,
                    "plan_step_id": step.step_id,
                },
            )
        return tuple(assignments)

    def _execute(
        self,
        context: CoordinationContext,
        assignments: tuple[AgentAssignment, ...],
        run_id: str,
    ):
        steps = {
            step.step_id: step for step in context.execution_plan.steps
        }
        final_assignments: list[AgentAssignment] = []
        results = []
        halted = False
        for assignment in assignments:
            if halted:
                final_assignments.append(
                    assignment.model_copy(
                        update={"status": AssignmentStatus.SKIPPED}
                    )
                )
                continue
            running = assignment.model_copy(
                update={"status": AssignmentStatus.RUNNING}
            )
            step = steps[assignment.plan_step_id]
            result = self._runtime.execute(
                AgentExecutionRequest(
                    execution_id=assignment.assignment_id,
                    agent_id=assignment.agent_id,
                    capability=AgentCapability(
                        id=assignment.required_capability
                    ),
                    input={
                        "plan_step": step.model_dump(mode="json"),
                        "memory": [
                            entry.model_dump(mode="json")
                            for entry in context.memory
                        ],
                    },
                    context={
                        "objective": step.description,
                        "workflow": dict(context.workflow),
                    },
                    workflow_execution_id=run_id,
                    workflow_step_id=step.step_id,
                    metadata={
                        **context.metadata,
                        "assignment_id": assignment.assignment_id,
                        "plan_step_id": step.step_id,
                    },
                    timeout_seconds=(
                        self._policy.logical_timeout_seconds
                    ),
                )
            )
            succeeded = (
                result.status is AgentExecutionStatus.SUCCEEDED
            )
            finished = running.model_copy(
                update={
                    "status": (
                        AssignmentStatus.COMPLETED
                        if succeeded
                        else AssignmentStatus.FAILED
                    )
                }
            )
            final_assignments.append(finished)
            results.append(result)
            self._record(
                run_id,
                TimelineEventType.ASSIGNMENT_COMPLETED,
                {
                    "assignment_id": assignment.assignment_id,
                    "status": finished.status.value,
                },
            )
            halted = self._policy.stop_on_failure and not succeeded
        return tuple(final_assignments), tuple(results)

    @staticmethod
    def _assignment_id(
        plan_id: str, step_id: str, agent_id: str
    ) -> str:
        digest = hashlib.sha256(
            f"{plan_id}:{step_id}:{agent_id}".encode("utf-8")
        ).hexdigest()
        return f"assignment-{digest[:24]}"

    def _record(
        self,
        run_id: str,
        event_type: TimelineEventType,
        metadata=None,
    ) -> None:
        self._timeline.record(
            run_id,
            event_type,
            message=event_type.value,
            metadata=metadata or {},
        )


__all__ = ["AgentCoordinator"]
