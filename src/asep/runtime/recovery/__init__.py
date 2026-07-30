"""API pública de Intelligent Execution & Recovery."""

from asep.runtime.recovery.backoff import (
    BackoffStrategy,
    ConstantBackoff,
    ExponentialBackoff,
    LinearBackoff,
)
from asep.runtime.recovery.classifier import FailureClassifier
from asep.runtime.recovery.contracts import ExecutionSupervisor
from asep.runtime.recovery.exceptions import (
    FailureClassificationError,
    InvalidStateTransitionError,
    RecoveryError,
    RecoveryPolicyError,
    RecoveryValidationError,
    RetryLimitExceededError,
)
from asep.runtime.recovery.metrics import (
    InMemoryRecoveryMetrics,
    RecoveryMetricsRecorder,
    RecoveryMetricsSnapshot,
)
from asep.runtime.recovery.models import (
    BackoffKind,
    FailureCategory,
    FallbackAction,
    FallbackPolicy,
    RecoveryContext,
    RecoveryPolicy,
    RecoveryResult,
    RetryDecision,
    RetryPolicy,
    SupervisedExecutionState,
)
from asep.runtime.recovery.service import (
    ExecutionRecoveryService,
    RecoveryService,
)
from asep.runtime.recovery.state_machine import ExecutionStateMachine
from asep.runtime.recovery.supervisor import (
    DefaultExecutionSupervisor,
)
from asep.runtime.recovery.validator import RecoveryValidator

__all__ = [
    "BackoffKind",
    "BackoffStrategy",
    "ConstantBackoff",
    "DefaultExecutionSupervisor",
    "ExecutionRecoveryService",
    "ExecutionStateMachine",
    "ExecutionSupervisor",
    "ExponentialBackoff",
    "FailureCategory",
    "FailureClassificationError",
    "FailureClassifier",
    "FallbackAction",
    "FallbackPolicy",
    "InMemoryRecoveryMetrics",
    "InvalidStateTransitionError",
    "LinearBackoff",
    "RecoveryContext",
    "RecoveryError",
    "RecoveryMetricsRecorder",
    "RecoveryMetricsSnapshot",
    "RecoveryPolicy",
    "RecoveryPolicyError",
    "RecoveryResult",
    "RecoveryService",
    "RecoveryValidationError",
    "RecoveryValidator",
    "RetryDecision",
    "RetryLimitExceededError",
    "RetryPolicy",
    "SupervisedExecutionState",
]
