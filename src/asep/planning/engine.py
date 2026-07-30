"""Planning Engine determinístico, observável e sem execução."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter

from asep.memory.contracts import AgentMemory
from asep.planning.contracts import PlanningStrategy
from asep.planning.exceptions import PlanningValidationError
from asep.planning.metrics import PlanningMetricsRecorder
from asep.planning.models import (
    ExecutionPlan,
    PlanningContext,
    PlanningPolicy,
    PlanningRequest,
    PlanningResult,
    PlanningStatistics,
)
from asep.planning.strategy import SequentialPlanningStrategy
from asep.planning.validator import PlanningValidator
from asep.timeline import TimelineEventType, TimelineRecorder
from asep.tools.registry import ToolRegistry

Clock = Callable[[], datetime]
Timer = Callable[[], float]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class _NullMetrics:
    def completed(self, *, steps: int, duration_seconds: float) -> None:
        del steps, duration_seconds

    def failed(self, *, duration_seconds: float) -> None:
        del duration_seconds


class PlanningEngine:
    def __init__(
        self,
        *,
        timeline: TimelineRecorder,
        strategy: PlanningStrategy | None = None,
        validator: PlanningValidator | None = None,
        policy: PlanningPolicy | None = None,
        metrics: PlanningMetricsRecorder | None = None,
        memory: AgentMemory | None = None,
        tool_registry: ToolRegistry | None = None,
        clock: Clock | None = None,
        timer: Timer | None = None,
    ) -> None:
        self._timeline = timeline
        self._strategy = strategy or SequentialPlanningStrategy()
        self._validator = validator or PlanningValidator()
        self._policy = policy or PlanningPolicy()
        self._metrics = metrics or _NullMetrics()
        self._memory = memory
        self._tool_registry = tool_registry
        self._clock = clock or _utc_now
        self._timer = timer or perf_counter

    def plan(self, request: PlanningRequest) -> PlanningResult:
        started = self._timer()
        run_id = request.workflow_execution_id or request.goal
        self._record(run_id, TimelineEventType.PLANNING_REQUESTED)
        self._record(run_id, TimelineEventType.PLANNING_STARTED)
        try:
            self._validator.validate_request(request)
            enriched = self._enrich(request)
            steps = self._strategy.build_steps(enriched, self._policy)
            estimated_cost = sum(step.estimated_cost for step in steps)
            estimated_duration = sum(
                step.estimated_duration_seconds for step in steps
            )
            plan = ExecutionPlan(
                plan_id=self._plan_id(enriched, steps),
                goal=enriched.goal,
                steps=steps,
                estimated_cost=estimated_cost,
                estimated_duration_seconds=estimated_duration,
                created_at=self._clock(),
                metadata={
                    "strategy": type(self._strategy).__name__,
                    "workflow_execution_id": enriched.workflow_execution_id,
                },
            )
            depth = self._validator.validate_plan(
                plan, enriched, self._policy
            )
        except Exception as exc:
            duration = max(0.0, self._timer() - started)
            self._metrics.failed(duration_seconds=duration)
            event_type = (
                TimelineEventType.PLAN_REJECTED
                if isinstance(exc, PlanningValidationError)
                else TimelineEventType.PLANNING_FAILED
            )
            self._timeline.record(
                run_id,
                event_type,
                message=event_type.value,
                metadata={"error_type": type(exc).__name__},
            )
            raise

        duration = max(0.0, self._timer() - started)
        statistics = PlanningStatistics(
            total_steps=len(steps),
            dependency_count=sum(len(step.dependencies) for step in steps),
            maximum_depth=depth,
            estimated_cost=estimated_cost,
            estimated_duration_seconds=estimated_duration,
            memory_entries_considered=len(enriched.context.memory),
        )
        warnings = tuple(
            message
            for condition, message in (
                (
                    not enriched.context.memory,
                    "Nenhuma memória operacional foi considerada.",
                ),
                (
                    any(step.tool_id is None for step in steps),
                    "Há passos sem Tool associada.",
                ),
            )
            if condition
        )
        self._record(
            run_id,
            TimelineEventType.PLAN_VALIDATED,
            {"plan_id": plan.plan_id, "steps": len(steps)},
        )
        self._record(
            run_id,
            TimelineEventType.PLANNING_COMPLETED,
            {
                "plan_id": plan.plan_id,
                "steps": len(steps),
                "duration_seconds": duration,
            },
        )
        self._metrics.completed(
            steps=len(steps), duration_seconds=duration
        )
        return PlanningResult(
            plan=plan,
            warnings=warnings,
            validation_messages=("Plano validado.",),
            statistics=statistics,
        )

    def _enrich(self, request: PlanningRequest) -> PlanningRequest:
        memories = request.context.memory
        if (
            not memories
            and self._memory is not None
            and request.agent_id is not None
        ):
            memories = self._memory.find_by_agent(request.agent_id)

        capabilities = set(request.context.available_capabilities)
        tools = dict(request.context.available_tools)
        if self._tool_registry is not None:
            for tool in self._tool_registry.list():
                for capability in tool.metadata.capabilities:
                    capabilities.add(capability.id)
                    tools.setdefault(capability.id, tool.metadata.id.value)

        context = PlanningContext.model_validate(
            {
                **request.context.model_dump(mode="python"),
                "memory": memories,
                "available_capabilities": tuple(sorted(capabilities)),
                "available_tools": tools,
            }
        )
        return PlanningRequest.model_validate(
            {
                **request.model_dump(mode="python"),
                "context": context,
            }
        )

    @staticmethod
    def _plan_id(request: PlanningRequest, steps) -> str:
        canonical = {
            "goal": request.goal,
            "workflow_execution_id": request.workflow_execution_id,
            "agent_id": (
                request.agent_id.value
                if request.agent_id is not None
                else None
            ),
            "steps": [step.model_dump(mode="json") for step in steps],
        }
        digest = hashlib.sha256(
            json.dumps(
                canonical,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return f"plan-{digest[:24]}"

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


__all__ = ["PlanningEngine"]
