"""Validação prévia das execuções de agentes."""

from __future__ import annotations

from asep.agents.contracts import Agent, AgentId
from asep.agents.exceptions import (
    AgentCapabilityNotSupportedError,
    AgentExecutionValidationError,
    AgentNotRegisteredError,
)
from asep.agents.registry import AgentNotFoundException, AgentRegistry
from asep.agents.runtime_models import (
    AgentExecutionPolicy,
    AgentExecutionRequest,
)


class AgentExecutionValidator:
    def validate(
        self,
        request: AgentExecutionRequest,
        policy: AgentExecutionPolicy,
        registry: AgentRegistry,
    ) -> Agent:
        if not isinstance(request, AgentExecutionRequest):
            raise AgentExecutionValidationError(
                "request deve ser AgentExecutionRequest válido."
            )
        if not isinstance(policy, AgentExecutionPolicy):
            raise AgentExecutionValidationError(
                "policy deve ser AgentExecutionPolicy válida."
            )
        try:
            agent = registry.get(AgentId(value=request.agent_id.value))
        except AgentNotFoundException as exc:
            raise AgentNotRegisteredError(
                f"Agente não registrado: {request.agent_id}"
            ) from exc
        if policy.validate_capability and not any(
            item.id == request.capability.id
            for item in agent.metadata.capabilities
        ):
            raise AgentCapabilityNotSupportedError(
                f"Agente {request.agent_id} não suporta a capability "
                f"{request.capability.id}."
            )
        return agent
