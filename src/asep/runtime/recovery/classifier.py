"""Classificação determinística de falhas."""

from asep.agents.exceptions import (
    AgentExecutionFailedError,
    AgentExecutionValidationError,
)
from asep.agents.runtime_models import (
    AgentExecutionResult,
    AgentExecutionStatus,
)
from asep.errors import ConfigurationError
from asep.runtime.recovery.exceptions import FailureClassificationError
from asep.runtime.recovery.models import FailureCategory
from asep.tools.exceptions import (
    ToolExecutionError,
    ToolTimeoutError,
    ToolValidationError,
)
from asep.workflow.exceptions import (
    WorkflowExecutionException,
    WorkflowValidationException,
)


class FailureClassifier:
    def classify(
        self, failure: BaseException | AgentExecutionResult
    ) -> FailureCategory:
        if isinstance(failure, AgentExecutionResult):
            if failure.status is AgentExecutionStatus.SUCCEEDED:
                raise FailureClassificationError(
                    "Resultado bem-sucedido não é uma falha."
                )
            if failure.status is AgentExecutionStatus.TIMED_OUT:
                return FailureCategory.TIMEOUT
            if failure.status is AgentExecutionStatus.REJECTED:
                return FailureCategory.VALIDATION
            if failure.status is AgentExecutionStatus.CANCELLED:
                return FailureCategory.WORKFLOW
            code = failure.error.code if failure.error else ""
            if code.startswith("tool_"):
                return FailureCategory.TOOL
            return FailureCategory.AGENT
        if isinstance(failure, (TimeoutError,)):
            return FailureCategory.TIMEOUT
        if isinstance(failure, (ToolTimeoutError,)):
            return FailureCategory.TIMEOUT
        if isinstance(failure, (ToolValidationError,)):
            return FailureCategory.VALIDATION
        if isinstance(failure, (ToolExecutionError,)):
            return FailureCategory.TOOL
        if isinstance(failure, (AgentExecutionValidationError,)):
            return FailureCategory.VALIDATION
        if isinstance(failure, (AgentExecutionFailedError,)):
            return FailureCategory.AGENT
        if isinstance(failure, (WorkflowValidationException,)):
            return FailureCategory.VALIDATION
        if isinstance(failure, (WorkflowExecutionException,)):
            return FailureCategory.WORKFLOW
        if isinstance(failure, (ConfigurationError,)):
            return FailureCategory.CONFIGURATION
        if isinstance(failure, (OSError, ConnectionError)):
            return FailureCategory.INFRASTRUCTURE
        if isinstance(failure, BaseException):
            return FailureCategory.UNEXPECTED
        raise FailureClassificationError("Falha inválida.")


__all__ = ["FailureClassifier"]
