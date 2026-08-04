"""Ciclo determinístico e limitado de reparo funcional."""

from __future__ import annotations

from asep.repair.contracts import RepairExecutor, RepairPlanner
from asep.repair.models import (
    RepairAttempt,
    RepairLoopContext,
    RepairResult,
    RepairStatus,
)


class RepairLoopService:
    """Planeja e executa reparos até sucesso ou exaustão explícita."""

    def __init__(
        self,
        planner: RepairPlanner,
        executor: RepairExecutor,
    ) -> None:
        self._planner = planner
        self._executor = executor

    def execute(self, context: RepairLoopContext) -> RepairResult:
        attempts: list[RepairAttempt] = []
        messages: list[str] = []
        analysis = context.initial_analysis

        for attempt_number in range(1, context.policy.max_attempts + 1):
            plan = self._planner.plan(analysis)
            execution = self._executor.execute(plan)

            recorded = execution.attempts or (
                RepairAttempt(
                    attempt=attempt_number,
                    plan=plan,
                    status=execution.status,
                    messages=execution.messages,
                ),
            )
            attempts.extend(
                item.model_copy(update={"attempt": attempt_number})
                for item in recorded
            )
            messages.extend(execution.messages)
            analysis = execution.final_analysis or analysis

            if execution.status is RepairStatus.SUCCEEDED:
                return RepairResult(
                    status=RepairStatus.SUCCEEDED,
                    attempts=tuple(attempts),
                    final_analysis=analysis,
                    messages=tuple(messages),
                )

        messages.append("Limite de tentativas de reparo atingido.")
        return RepairResult(
            status=RepairStatus.EXHAUSTED,
            attempts=tuple(attempts),
            final_analysis=analysis,
            messages=tuple(messages),
        )


__all__ = ["RepairLoopService"]
