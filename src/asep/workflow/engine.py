"""Fachada do Workflow Engine genérico."""

from asep.workflow.models import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowExecutionResult,
)
from asep.workflow.executor import WorkflowExecutor
from asep.workflow.validator import WorkflowValidator


class WorkflowEngine:
    def __init__(
        self,
        validator: WorkflowValidator,
        executor: WorkflowExecutor,
    ) -> None:
        self._validator = validator
        self._executor = executor

    def execute(
        self,
        workflow: WorkflowDefinition | None,
        context: WorkflowContext,
    ) -> WorkflowExecutionResult:
        validated = self._validator.validate(workflow)
        return self._executor.execute(validated, context)
