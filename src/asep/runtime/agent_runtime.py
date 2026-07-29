"""Runtime genérico e local para agentes ASEP."""

from __future__ import annotations

import logging
from typing import Protocol

from pydantic import ValidationError

from asep.errors import (
    AgentContractError,
    AgentExecutionError,
    AgentNotFoundError,
    AgentResultError,
)
from asep.execution.models import AgentContext, AgentResult
from asep.models import RegistrySnapshot


class Agent(Protocol):
    id: str

    def execute(self, context: AgentContext) -> AgentResult: ...


class AgentRuntime:
    def __init__(self, agents: dict[str, Agent]) -> None:
        self._agents = agents

    def execute(
        self,
        context: AgentContext,
        registry: RegistrySnapshot,
        logger: logging.Logger,
    ) -> AgentResult:
        if context.agent_id not in registry.agents:
            raise AgentNotFoundError(
                f"Agente não registrado: {context.agent_id}"
            )
        if context.agent_id not in registry.contracts:
            raise AgentContractError(
                f"Contrato não registrado para agente: {context.agent_id}"
            )
        agent = self._agents.get(context.agent_id)
        if agent is None:
            raise AgentNotFoundError(
                f"Agente não possui adaptador executável: {context.agent_id}"
            )
        logger.info(
            "Agente iniciado.",
            extra={
                "event_type": "agent_started",
                "project_id": context.project_id,
                "workflow_id": context.workflow_id,
                "stage_id": context.stage_id,
                "agent_id": context.agent_id,
            },
        )
        try:
            raw_result = agent.execute(context)
            result = AgentResult.model_validate(raw_result)
        except ValidationError as exc:
            raise AgentResultError(
                f"Resultado inválido do agente {context.agent_id}."
            ) from exc
        except Exception as exc:
            raise AgentExecutionError(
                f"Falha controlada no agente {context.agent_id}: "
                f"{type(exc).__name__}"
            ) from exc
        if (
            result.run_id != context.run_id
            or result.stage_id != context.stage_id
            or result.agent_id != context.agent_id
        ):
            raise AgentResultError(
                "Identidade do AgentResult diverge do AgentContext."
            )
        logger.info(
            "Agente concluído.",
            extra={
                "event_type": "agent_completed",
                "project_id": context.project_id,
                "workflow_id": context.workflow_id,
                "stage_id": context.stage_id,
                "agent_id": context.agent_id,
            },
        )
        return result
