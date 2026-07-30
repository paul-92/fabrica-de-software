"""Exceções tipadas da fronteira de Tools."""


class ToolException(Exception):
    """Base para falhas de Tool."""


class ToolValidationError(ToolException):
    """Request, payload ou workspace inválido."""


class ToolNotRegisteredError(ToolValidationError):
    """ToolId não está no Registry."""


class ToolCapabilityNotSupportedError(ToolValidationError):
    """A Tool não declara a capability solicitada."""


class ToolAlreadyRegisteredError(ToolException):
    """ToolId duplicado."""


class InvalidToolRegistrationError(ToolException):
    """Objeto não satisfaz o contrato Tool."""


class ToolExecutionError(ToolException):
    """Falha classificada durante execução."""

    def __init__(
        self,
        tool_id: str,
        *,
        error_type: str,
        retryable: bool = False,
    ) -> None:
        self.tool_id = tool_id
        self.error_type = error_type
        self.retryable = retryable
        super().__init__(f"Execução da Tool {tool_id} falhou ({error_type}).")


class ToolTimeoutError(ToolExecutionError):
    """A Tool excedeu o timeout."""


class ToolRetryExhaustedError(ToolExecutionError):
    """As tentativas da Tool foram esgotadas."""


class ToolSecurityError(ToolValidationError):
    """Acesso rejeitado pela fronteira de workspace."""


class ToolDuplicateExecutionError(ToolException):
    """execution_id já está em andamento na instância."""


__all__ = [
    "InvalidToolRegistrationError",
    "ToolAlreadyRegisteredError",
    "ToolCapabilityNotSupportedError",
    "ToolDuplicateExecutionError",
    "ToolException",
    "ToolExecutionError",
    "ToolNotRegisteredError",
    "ToolRetryExhaustedError",
    "ToolSecurityError",
    "ToolTimeoutError",
    "ToolValidationError",
]
