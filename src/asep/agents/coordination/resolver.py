"""Resolução determinística de capabilities para agentes registrados."""

from asep.agents.contracts import AgentCapability, AgentId
from asep.agents.coordination.exceptions import CapabilityResolutionError
from asep.agents.coordination.models import AgentSelectionPolicy
from asep.agents.registry import AgentRegistry
from asep.planning.models import PlanStep


class RegistryAgentCapabilityResolver:
    def __init__(
        self,
        registry: AgentRegistry,
        policy: AgentSelectionPolicy | None = None,
        *,
        allow_fallback: bool = True,
    ) -> None:
        self._registry = registry
        self._policy = policy or AgentSelectionPolicy()
        self._allow_fallback = allow_fallback

    def resolve(self, step: PlanStep) -> AgentId:
        explicit = step.agent_id
        if explicit is not None and self._policy.prefer_explicit_agent:
            if self._eligible(explicit, step.required_capability):
                return explicit
            if not self._allow_fallback:
                raise CapabilityResolutionError(
                    f"Agente explícito inelegível: {explicit}."
                )

        affinity = self._policy.affinity.get(step.required_capability)
        if affinity:
            candidate = AgentId(value=affinity)
            if self._eligible(candidate, step.required_capability):
                return candidate

        candidates = self._registry.find_by_capability(
            AgentCapability(id=step.required_capability)
        )
        available = tuple(
            agent
            for agent in candidates
            if (
                not self._policy.require_available
                or agent.metadata.id.value
                not in self._policy.unavailable_agents
            )
        )
        if not available:
            raise CapabilityResolutionError(
                "Nenhum agente disponível para capability "
                f"{step.required_capability}."
            )
        return available[0].metadata.id

    def _eligible(self, agent_id: AgentId, capability: str) -> bool:
        if (
            self._policy.require_available
            and agent_id.value in self._policy.unavailable_agents
        ):
            return False
        if not self._registry.contains(agent_id):
            return False
        return any(
            item.id == capability
            for item in self._registry.get_metadata(agent_id).capabilities
        )


__all__ = ["RegistryAgentCapabilityResolver"]
