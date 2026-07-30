"""Erros do sistema central de configuração."""

from asep.errors import ConfigurationError


class ConfigurationValidationError(ConfigurationError):
    """Configuração inválida fornecida por defaults ou ambiente."""

    code = "APPLICATION_CONFIGURATION_INVALID"
    category = "validation"
    next_action = (
        "Corrija as variáveis ASEP_STORAGE_* e reinicie a aplicação."
    )
    exit_code = 3
