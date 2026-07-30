"""Adapter entre o contrato Agent e o contrato WorkflowStep."""

from __future__ import annotations

from pydantic import ValidationError

from asep.agents.contracts import Agent, AgentRequest
from asep.agents.exceptions import (
    AgentExecutionException,
    AgentValidationException,
)
from asep.execution.models import AgentContext, AgentResult
from asep.workflow.models import WorkflowContext


class AgentStepAdapter:
    """Expõe uma execução de Agent como uma WorkflowStep síncrona."""

    def __init__(
        self,
        *,
        step_id: str,
        agent: Agent,
        request: AgentRequest,
        context: AgentContext,
        result_key: str | None = None,
    ) -> None:
        if not step_id.strip():
            raise AgentValidationException("step_id não pode ser vazio")
        if str(agent.metadata.id) != context.agent_id:
            raise AgentValidationException(
                "Identidade do Agent diverge do AgentContext."
            )
        self.id = step_id
        self._agent = agent
        self._request = request
        self._context = context
        self._result_key = result_key or f"agent_results.{step_id}"

    def execute(self, context: WorkflowContext) -> None:
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


__all__ = ["AgentStepAdapter"]
