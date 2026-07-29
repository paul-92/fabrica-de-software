"""Erros de domínio limitados à integração com providers."""

from asep.errors import AsepError


class ProviderError(AsepError):
    code = "PROVIDER_ERROR"
    category = "execution"
    next_action = "Verifique a configuração e os registros do provider."
    exit_code = 5


class ProviderUnavailableError(ProviderError):
    code = "PROVIDER_UNAVAILABLE"
    category = "blocked"
    retryable = True
    next_action = "Disponibilize o provider antes de repetir a execução."
    exit_code = 4


class ProviderExecutionError(ProviderError):
    code = "PROVIDER_EXECUTION_FAILED"
    retryable = True
    next_action = "Corrija a falha reportada pelo provider antes de repetir."


class ProviderProtocolError(ProviderError):
    code = "PROVIDER_PROTOCOL_INVALID"
    category = "validation"
    next_action = "Corrija o adaptador para respeitar o contrato do provider."
    exit_code = 3
