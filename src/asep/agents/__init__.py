"""Contratos e implementações de agentes da ASEP."""

from asep.agents.contracts import (
    Agent,
    AgentCapability,
    AgentContext,
    AgentError,
    AgentId,
    AgentMetadata,
    AgentRequest,
    AgentResult,
    AgentStatus,
)
from asep.agents.exceptions import (
    AgentCapabilityNotSupportedError,
    AgentDuplicateExecutionError,
    AgentException,
    AgentExecutionCancelledError,
    AgentExecutionException,
    AgentExecutionFailedError,
    AgentExecutionTimeoutError,
    AgentExecutionValidationError,
    AgentNotRegisteredError,
    AgentRetryExhaustedError,
    AgentRuntimeError,
    AgentValidationException,
)
from asep.agents.execution_service import AgentExecutionService
from asep.agents.registry import (
    AgentAlreadyRegisteredException,
    AgentNotFoundException,
    AgentRegistry,
    AgentRegistryException,
    InMemoryAgentRegistry,
    InvalidAgentRegistrationException,
)
from asep.agents.runtime import AgentRuntime
from asep.agents.runtime_metrics import (
    AgentExecutionMetricsRecorder,
    AgentExecutionMetricsSnapshot,
    InMemoryAgentExecutionMetrics,
    PerAgentExecutionMetricsSnapshot,
)
from asep.agents.runtime_models import (
    AgentExecutionContext,
    AgentExecutionPolicy,
    AgentExecutionRequest,
    AgentExecutionResult,
    AgentExecutionStatus,
)
from asep.agents.validator import AgentExecutionValidator

__all__ = [
    "Agent",
    "AgentAlreadyRegisteredException",
    "AgentCapabilityNotSupportedError",
    "AgentCapability",
    "AgentContext",
    "AgentError",
    "AgentException",
    "AgentDuplicateExecutionError",
    "AgentExecutionCancelledError",
    "AgentExecutionContext",
    "AgentExecutionException",
    "AgentExecutionFailedError",
    "AgentExecutionMetricsRecorder",
    "AgentExecutionMetricsSnapshot",
    "AgentExecutionPolicy",
    "AgentExecutionRequest",
    "AgentExecutionResult",
    "AgentExecutionService",
    "AgentExecutionStatus",
    "AgentExecutionTimeoutError",
    "AgentExecutionValidationError",
    "AgentExecutionValidator",
    "AgentId",
    "AgentMetadata",
    "AgentNotRegisteredError",
    "AgentNotFoundException",
    "AgentRequest",
    "AgentResult",
    "AgentRetryExhaustedError",
    "AgentRegistry",
    "AgentRegistryException",
    "AgentRuntime",
    "AgentRuntimeError",
    "AgentStatus",
    "AgentStepAdapter",
    "AgentValidationException",
    "InMemoryAgentRegistry",
    "InMemoryAgentExecutionMetrics",
    "PerAgentExecutionMetricsSnapshot",
    "InvalidAgentRegistrationException",
]


def __getattr__(name: str):
    if name == "AgentStepAdapter":
        from asep.agents.step_adapter import AgentStepAdapter

        return AgentStepAdapter
    raise AttributeError(name)
