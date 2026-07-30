"""Adapter entre o contrato Agent e o contrato WorkflowStep."""

from __future__ import annotations

from pydantic import ValidationError

from asep.agents.contracts import Agent, AgentRequest
from asep.agents.exceptions import (
    AgentExecutionException,
    AgentRuntimeError,
    AgentValidationException,
)
from asep.agents.runtime import AgentRuntime
from asep.agents.runtime_models import (
    AgentExecutionRequest,
    AgentExecutionStatus,
)
from asep.execution.models import AgentContext, AgentResult
from asep.workflow.models import WorkflowContext


class AgentStepAdapter:
    """Expõe uma execução de Agent como uma WorkflowStep síncrona."""

    def __init__(
        self,
        *,
        step_id: str,
        agent: Agent | None = None,
        request: AgentRequest | None = None,
        context: AgentContext | None = None,
        runtime: AgentRuntime | None = None,
        execution_request: AgentExecutionRequest | None = None,
        result_key: str | None = None,
    ) -> None:
        if not step_id.strip():
            raise AgentValidationException("step_id não pode ser vazio")
        direct_mode = all(
            value is not None for value in (agent, request, context)
        )
        runtime_mode = runtime is not None and execution_request is not None
        if direct_mode == runtime_mode:
            raise AgentValidationException(
                "Configure execução direta ou runtime, exclusivamente."
            )
        if direct_mode and (
            str(agent.metadata.id) != context.agent_id  # type: ignore[union-attr]
        ):
            raise AgentValidationException(
                "Identidade do Agent diverge do AgentContext."
            )
        self.id = step_id
        self._agent = agent
        self._request = request
        self._context = context
        self._runtime = runtime
        self._execution_request = execution_request
        self._result_key = result_key or f"agent_results.{step_id}"

    def execute(self, context: WorkflowContext) -> None:
        if self._runtime is not None:
            self._execute_runtime(context)
            return
        assert self._context is not None
        assert self._agent is not None
        assert self._request is not None
        if context.run_id != self._context.run_id:
            raise AgentValidationException(
                "run_id do WorkflowContext diverge do AgentContext."
            )

        try:
            raw_result = self._agent.execute(
                self._request,
                self._context,
            )
            result = AgentResult.model_validate(raw_result)
        except ValidationError as exc:
            raise AgentValidationException(
                f"Resultado inválido do agente {self._context.agent_id}."
            ) from exc
        except AgentValidationException:
            raise
        except Exception as exc:
            raise AgentExecutionException(
                self._context.agent_id,
                exc,
            ) from exc

        if (
            result.run_id != self._context.run_id
            or result.stage_id != self._context.stage_id
            or result.agent_id != self._context.agent_id
        ):
            raise AgentValidationException(
                "Identidade do AgentResult diverge do AgentContext."
            )

        context.values[self._result_key] = result

    def _execute_runtime(self, context: WorkflowContext) -> None:
        assert self._runtime is not None
        assert self._execution_request is not None
        expected_run = (
            self._execution_request.workflow_execution_id
            or self._execution_request.execution_id
        )
        if context.run_id != expected_run:
            raise AgentValidationException(
                "run_id do WorkflowContext diverge da AgentExecutionRequest."
            )
        result = self._runtime.execute(self._execution_request)
        context.values[self._result_key] = result
        if result.status is not AgentExecutionStatus.SUCCEEDED:
            raise AgentExecutionException(
                result.agent_id.value,
                AgentRuntimeError(
                    f"Runtime terminou com status {result.status.value}."
                ),
            )


__all__ = ["AgentStepAdapter"]
