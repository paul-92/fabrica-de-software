"""Exceções específicas dos contratos formais de agentes."""

from __future__ import annotations


class AgentException(Exception):
    """Base para falhas na fronteira de agentes."""


class AgentValidationException(AgentException):
    """Contrato, identidade ou resultado de agente inválido."""


class AgentExecutionException(AgentException):
    """Falha inesperada durante a execução de um agente."""

    def __init__(self, agent_id: str, cause: Exception) -> None:
        self.agent_id = agent_id
        self.cause = cause
        super().__init__(
            f"Falha ao executar agente {agent_id}: "
            f"{type(cause).__name__}: {cause}"
        )
