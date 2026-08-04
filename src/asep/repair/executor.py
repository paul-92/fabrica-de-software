"""Execução controlada de planos de reparo."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from asep.repair.models import (
    RepairAttempt,
    RepairPlan,
    RepairResult,
    RepairStatus,
)
from asep.tools.contracts import ToolExecutor
from asep.tools.models import (
    ToolCapability,
    ToolExecutionStatus,
    ToolId,
    ToolRequest,
)


class ControlledRepairExecutor:
    """Aplica alterações de um RepairPlan por meio de Tools."""

    def __init__(
        self,
        tool_executor: ToolExecutor,
        workspace: Path,
    ) -> None:
        self._tool_executor = tool_executor
        self._workspace = workspace
        self._execution_number = 0

    def execute(
        self,
        plan: RepairPlan,
    ) -> RepairResult:
        self._execution_number += 1
        execution_prefix = f"repair-{self._execution_number}"
        messages: list[str] = []

        for index, change in enumerate(
            plan.changes,
            start=1,
        ):
            try:
                result = self._tool_executor.execute(
                    ToolRequest(
                        execution_id=f"{execution_prefix}-change-{index}",
                        tool_id=ToolId(
                            value="write-file",
                        ),
                        capability=ToolCapability(
                            id="write_file",
                        ),
                        workspace=self._workspace,
                        payload={
                            "path": change.path,
                            "content": change.content,
                            "overwrite": change.overwrite,
                        },
                        metadata={
                            "reason": change.reason,
                        },
                        workflow_execution_id="repair",
                    )
                )
            except Exception as exc:
                return self._failed_result(
                    plan=plan,
                    path=change.path,
                    message=str(exc),
                )

            if result.status is not ToolExecutionStatus.SUCCEEDED:
                error_message = (
                    result.error.message
                    if result.error is not None
                    else "A Tool retornou status de falha."
                )

                return self._failed_result(
                    plan=plan,
                    path=change.path,
                    message=error_message,
                )

            messages.append(
                f"Alteração aplicada em {change.path}."
            )

        try:
            validation = self._tool_executor.execute(
                ToolRequest(
                    execution_id=f"{execution_prefix}-validation",
                    tool_id=ToolId(value="run-tests"),
                    capability=ToolCapability(id="test"),
                    workspace=self._workspace,
                    payload={"paths": list(plan.test_paths)},
                    metadata={"repair": True},
                    workflow_execution_id="repair",
                )
            )
        except Exception as exc:
            return self._failed_result(
                plan=plan,
                path="<validation>",
                message=str(exc),
            )

        validation_output = self._validation_output(validation.output)

        if validation.status is not ToolExecutionStatus.SUCCEEDED:
            error_message = (
                validation.error.message
                if validation.error is not None
                else "A validação retornou status de falha."
            )
            return self._failed_result(
                plan=plan,
                path="<validation>",
                message=error_message,
                validation_output=validation_output,
            )

        messages.append("Testes de validação concluídos com sucesso.")

        attempt = RepairAttempt(
            attempt=1,
            plan=plan,
            status=RepairStatus.SUCCEEDED,
            validation_output=validation_output,
            messages=tuple(messages),
        )

        return RepairResult(
            status=RepairStatus.SUCCEEDED,
            attempts=(attempt,),
            final_analysis=plan.analysis,
            messages=tuple(messages),
        )

    @staticmethod
    def _failed_result(
        *,
        plan: RepairPlan,
        path: str,
        message: str,
        validation_output: str = "",
    ) -> RepairResult:
        attempt_messages = (
            f"Falha ao aplicar alteração em {path}: {message}",
        )

        attempt = RepairAttempt(
            attempt=1,
            plan=plan,
            status=RepairStatus.FAILED,
            validation_output=validation_output,
            messages=attempt_messages,
        )

        return RepairResult(
            status=RepairStatus.FAILED,
            attempts=(attempt,),
            final_analysis=plan.analysis,
            messages=attempt_messages,
        )

    @staticmethod
    def _validation_output(output: object) -> str:
        if not isinstance(output, Mapping):
            return ""

        parts = [
            value.strip()
            for key in ("stdout", "stderr")
            if isinstance((value := output.get(key)), str)
            and value.strip()
        ]
        return "\n".join(parts)


__all__ = [
    "ControlledRepairExecutor",
]
