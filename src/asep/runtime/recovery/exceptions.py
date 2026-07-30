"""Exceções da supervisão e recuperação determinísticas."""


class RecoveryError(Exception):
    """Falha base do subsistema de recuperação."""


class RetryLimitExceededError(RecoveryError):
    """O limite configurado de tentativas foi atingido."""


class InvalidStateTransitionError(RecoveryError):
    """Transição não permitida pela máquina de estados."""


class RecoveryPolicyError(RecoveryError):
    """Política de retry ou fallback inconsistente."""


class FailureClassificationError(RecoveryError):
    """A falha recebida não pôde ser classificada."""


class RecoveryValidationError(RecoveryError):
    """Contexto de recuperação inválido."""


__all__ = [
    "FailureClassificationError",
    "InvalidStateTransitionError",
    "RecoveryError",
    "RecoveryPolicyError",
    "RecoveryValidationError",
    "RetryLimitExceededError",
]
