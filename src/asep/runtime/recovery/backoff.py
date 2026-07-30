"""Estratégias puras de backoff."""

from typing import Protocol, runtime_checkable

from asep.runtime.recovery.models import RetryPolicy


@runtime_checkable
class BackoffStrategy(Protocol):
    def delay(self, attempt: int, policy: RetryPolicy) -> float: ...


class ConstantBackoff:
    def delay(self, attempt: int, policy: RetryPolicy) -> float:
        del attempt
        return _limited(policy.interval_seconds, policy)


class LinearBackoff:
    def delay(self, attempt: int, policy: RetryPolicy) -> float:
        return _limited(policy.interval_seconds * attempt, policy)


class ExponentialBackoff:
    def delay(self, attempt: int, policy: RetryPolicy) -> float:
        return _limited(
            policy.interval_seconds * (2 ** max(0, attempt - 1)),
            policy,
        )


def _limited(delay: float, policy: RetryPolicy) -> float:
    if policy.max_delay_seconds is None:
        return delay
    return min(delay, policy.max_delay_seconds)


__all__ = [
    "BackoffStrategy",
    "ConstantBackoff",
    "ExponentialBackoff",
    "LinearBackoff",
]
