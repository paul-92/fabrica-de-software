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


class AgentRuntimeError(AgentException):
    """Base das falhas do runtime inteligente."""


class AgentExecutionValidationError(
    AgentRuntimeError,
    AgentValidationException,
):
    """A solicitação não pode ser executada com segurança."""


class AgentNotRegisteredError(AgentExecutionValidationError):
    """AgentId não está disponível no Registry."""


class AgentCapabilityNotSupportedError(AgentExecutionValidationError):
    """Agente não declara a capacidade solicitada."""


class AgentExecutionFailedError(AgentRuntimeError):
    """Falha de execução classificada pelo runtime."""

    def __init__(
        self,
        agent_id: str,
        *,
        error_type: str,
        retryable: bool = False,
    ) -> None:
        self.agent_id = agent_id
        self.error_type = error_type
        self.retryable = retryable
        super().__init__(
            f"Execução do agente {agent_id} falhou ({error_type})."
        )


class AgentExecutionTimeoutError(AgentRuntimeError):
    """Execução excedeu o limite síncrono configurado."""


class AgentExecutionCancelledError(AgentRuntimeError):
    """Execução foi cancelada antes de iniciar."""


class AgentRetryExhaustedError(AgentRuntimeError):
    """Todas as tentativas permitidas falharam."""


class AgentDuplicateExecutionError(AgentRuntimeError):
    """O mesmo execution_id já está em andamento nesta instância."""
