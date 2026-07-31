"""API pública da coordenação determinística de agentes."""
from asep.agents.coordination.adapter import AgentCoordinatorAdapter

from asep.agents.coordination.aggregator import (
    DeterministicResultAggregator,
)
from asep.agents.coordination.contracts import (
    AgentCapabilityResolver,
    AgentExecutionResultAggregator,
    Coordinator,
)
from asep.agents.coordination.coordinator import AgentCoordinator
from asep.agents.coordination.exceptions import (
    AgentAssignmentError,
    CapabilityResolutionError,
    CoordinationError,
    CoordinationValidationError,
    ResultAggregationError,
)
from asep.agents.coordination.metrics import (
    CoordinationMetricsRecorder,
    CoordinationMetricsSnapshot,
    InMemoryCoordinationMetrics,
)
from asep.agents.coordination.models import (
    AgentAssignment,
    AgentSelectionPolicy,
    AssignmentStatus,
    CoordinationContext,
    CoordinationPolicy,
    CoordinationResult,
    CoordinationStatistics,
    CoordinationStatus,
)
from asep.agents.coordination.queue import AgentExecutionQueue
from asep.agents.coordination.resolver import (
    RegistryAgentCapabilityResolver,
)
from asep.agents.coordination.validator import CoordinationValidator

__all__ = [
    "AgentAssignment",
    "AgentAssignmentError",
    "AgentCapabilityResolver",
    "AgentCoordinator",
    "AgentCoordinatorAdapter",
    "AgentExecutionQueue",
    "AgentExecutionResultAggregator",
    "AgentSelectionPolicy",
    "AssignmentStatus",
    "CapabilityResolutionError",
    "CoordinationContext",
    "CoordinationError",
    "CoordinationMetricsRecorder",
    "CoordinationMetricsSnapshot",
    "CoordinationPolicy",
    "CoordinationResult",
    "CoordinationStatistics",
    "CoordinationStatus",
    "CoordinationValidationError",
    "CoordinationValidator",
    "Coordinator",
    "DeterministicResultAggregator",
    "InMemoryCoordinationMetrics",
    "RegistryAgentCapabilityResolver",
    "ResultAggregationError",
]
