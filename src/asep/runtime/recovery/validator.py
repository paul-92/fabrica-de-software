"""Validação defensiva da recuperação."""

from asep.runtime.recovery.exceptions import (
    RecoveryPolicyError,
    RecoveryValidationError,
)
from asep.runtime.recovery.models import (
    FallbackAction,
    RecoveryContext,
    RecoveryPolicy,
)


class RecoveryValidator:
    def validate(
        self, context: RecoveryContext, policy: RecoveryPolicy
    ) -> None:
        if not isinstance(context, RecoveryContext):
            raise RecoveryValidationError(
                "context deve ser RecoveryContext."
            )
        if not isinstance(policy, RecoveryPolicy):
            raise RecoveryPolicyError(
                "policy deve ser RecoveryPolicy."
            )
        if context.attempts >= policy.retry.max_attempts:
            raise RecoveryPolicyError(
                "tentativas iniciais atingem o limite de retry."
            )
        fallback = policy.fallback
        if (
            fallback.action is FallbackAction.SUBSTITUTE_AGENT
            and fallback.replacement_agent_id == context.request.agent_id
        ):
            raise RecoveryPolicyError(
                "agente de fallback deve ser diferente do atual."
            )
        if (
            fallback.action is FallbackAction.ALTERNATIVE_STEP
            and fallback.alternative_capability
            == context.request.capability.id
        ):
            raise RecoveryPolicyError(
                "etapa alternativa deve possuir outra capability."
            )


__all__ = ["RecoveryValidator"]
