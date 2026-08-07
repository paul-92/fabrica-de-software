"""Erros neutros da fronteira de AI Runtime."""

from __future__ import annotations


class AIRuntimeError(Exception):
    """Base segura: mensagens não incorporam payloads nem segredos."""

    message = "Falha no AI Runtime."

    def __init__(self, runtime_id: str | None = None) -> None:
        self.runtime_id = runtime_id
        suffix = f" Runtime: {runtime_id}." if runtime_id else ""
        super().__init__(f"{self.message}{suffix}")


class AIRuntimeConfigurationError(AIRuntimeError):
    message = "Configuração do AI Runtime inválida."


class AIRuntimeAuthenticationError(AIRuntimeError):
    message = "Autenticação do AI Runtime falhou."


class AIRuntimeUnavailableError(AIRuntimeError):
    message = "AI Runtime indisponível."


class AIRuntimeRateLimitError(AIRuntimeError):
    message = "Limite de uso do AI Runtime atingido."


class AIRuntimeTimeoutError(AIRuntimeError):
    message = "AI Runtime excedeu o tempo limite."


class AIRuntimeInvalidResponseError(AIRuntimeError):
    message = "AI Runtime retornou uma resposta inválida."


class AIRuntimeUnexpectedError(AIRuntimeError):
    message = "AI Runtime falhou inesperadamente."

    def __init__(self, runtime_id: str | None, cause: BaseException) -> None:
        self.cause_type = type(cause).__name__
        super().__init__(runtime_id)


class AIRuntimeRegistryError(AIRuntimeError):
    message = "Falha no registro de AI Runtime."


class AIRuntimeAlreadyRegisteredError(AIRuntimeRegistryError):
    message = "AI Runtime já registrado."


class AIRuntimeNotFoundError(AIRuntimeRegistryError):
    message = "AI Runtime não encontrado."


__all__ = [name for name in globals() if name.startswith("AIRuntime")]
