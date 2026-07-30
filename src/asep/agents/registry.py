"""Registry em memória para agentes que implementam o contrato ASEP."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from asep.agents.contracts import (
    Agent,
    AgentCapability,
    AgentId,
    AgentMetadata,
)


class AgentRegistryException(Exception):
    """Base para erros do Agent Registry."""


class AgentAlreadyRegisteredException(AgentRegistryException):
    """Um AgentId já está associado a outro agente."""

    def __init__(self, agent_id: AgentId) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agente já registrado: {agent_id}")


class AgentNotFoundException(AgentRegistryException):
    """O AgentId solicitado não existe neste Registry."""

    def __init__(self, agent_id: AgentId) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agente não encontrado: {agent_id}")


class InvalidAgentRegistrationException(AgentRegistryException):
    """O objeto não satisfaz o contrato formal de Agent."""


@runtime_checkable
class AgentRegistry(Protocol):
    """Porta de registro e consulta de agentes."""

    def register(self, agent: Agent) -> None: ...

    def unregister(self, agent_id: AgentId) -> None: ...

    def get(self, agent_id: AgentId) -> Agent: ...

    def contains(self, agent_id: AgentId) -> bool: ...

    def list_all(self) -> tuple[Agent, ...]: ...

    def get_metadata(self, agent_id: AgentId) -> AgentMetadata: ...

    def find_by_capability(
        self,
        capability: AgentCapability,
    ) -> tuple[Agent, ...]: ...


class InMemoryAgentRegistry:
    """Registry isolado, determinístico e sem estado global."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        metadata = self._validate_agent(agent)
        key = metadata.id.value
        if key in self._agents:
            raise AgentAlreadyRegisteredException(metadata.id)
        self._agents[key] = agent

    def unregister(self, agent_id: AgentId) -> None:
        key = self._validate_agent_id(agent_id).value
        if key not in self._agents:
            raise AgentNotFoundException(agent_id)
        del self._agents[key]

    def get(self, agent_id: AgentId) -> Agent:
        key = self._validate_agent_id(agent_id).value
        try:
            return self._agents[key]
        except KeyError as exc:
            raise AgentNotFoundException(agent_id) from exc

    def contains(self, agent_id: AgentId) -> bool:
        key = self._validate_agent_id(agent_id).value
        return key in self._agents

    def list_all(self) -> tuple[Agent, ...]:
        return tuple(self._agents[key] for key in sorted(self._agents))

    def get_metadata(self, agent_id: AgentId) -> AgentMetadata:
        return self.get(agent_id).metadata

    def find_by_capability(
        self,
        capability: AgentCapability,
    ) -> tuple[Agent, ...]:
        if not isinstance(capability, AgentCapability):
            raise InvalidAgentRegistrationException(
                "capability deve ser uma AgentCapability válida."
            )
        return tuple(
            agent
            for agent in self.list_all()
            if any(
                declared.id == capability.id
                for declared in agent.metadata.capabilities
            )
        )

    @staticmethod
    def _validate_agent(agent: Agent) -> AgentMetadata:
        if agent is None:
            raise InvalidAgentRegistrationException(
                "Agente não pode ser nulo."
            )
        try:
            metadata = agent.metadata
        except Exception as exc:
            raise InvalidAgentRegistrationException(
                "Não foi possível consultar os metadados do agente."
            ) from exc
        if not isinstance(metadata, AgentMetadata):
            raise InvalidAgentRegistrationException(
                "Agente deve expor AgentMetadata válido."
            )
        if not callable(getattr(agent, "execute", None)):
            raise InvalidAgentRegistrationException(
                "Agente deve implementar execute(request, context)."
            )
        return metadata

    @staticmethod
    def _validate_agent_id(agent_id: AgentId) -> AgentId:
        if not isinstance(agent_id, AgentId):
            raise InvalidAgentRegistrationException(
                "agent_id deve ser um AgentId válido."
            )
        return agent_id


__all__ = [
    "AgentAlreadyRegisteredException",
    "AgentNotFoundException",
    "AgentRegistry",
    "AgentRegistryException",
    "InMemoryAgentRegistry",
    "InvalidAgentRegistrationException",
]
