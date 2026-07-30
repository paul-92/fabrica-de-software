"""Fronteira de execução de uma única WorkflowStep."""

from asep.workflow.exceptions import WorkflowStepException
from asep.workflow.models import WorkflowContext, WorkflowStep


class WorkflowStepExecutor:
    def execute(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> None:
        try:
            step.execute(context)
        except Exception as exc:
            raise WorkflowStepException(step.id, exc) from exc
