"""Validação estrutural de WorkflowDefinition."""

from __future__ import annotations

from asep.workflow.exceptions import WorkflowValidationException
from asep.workflow.models import WorkflowDefinition, WorkflowStep


class WorkflowValidator:
    def validate(
        self,
        workflow: WorkflowDefinition | None,
    ) -> WorkflowDefinition:
        if workflow is None:
            raise WorkflowValidationException(
                "Workflow não pode ser nulo."
            )
        if not isinstance(workflow.id, str) or not workflow.id.strip():
            raise WorkflowValidationException(
                "Workflow deve possuir id não vazio."
            )
        if workflow.name is not None and not workflow.name.strip():
            raise WorkflowValidationException(
                "Workflow name não pode ser vazio."
            )
        if not workflow.steps:
            raise WorkflowValidationException(
                "Workflow deve possuir ao menos uma Step."
            )
        identifiers: list[str] = []
        for position, step in enumerate(workflow.steps):
            if not isinstance(step, WorkflowStep):
                raise WorkflowValidationException(
                    f"Step na posição {position} é inválida."
                )
            if not isinstance(step.id, str) or not step.id.strip():
                raise WorkflowValidationException(
                    f"Step na posição {position} possui id inválido."
                )
            identifiers.append(step.id)
        duplicates = sorted(
            identifier
            for identifier in set(identifiers)
            if identifiers.count(identifier) > 1
        )
        if duplicates:
            raise WorkflowValidationException(
                f"Workflow possui IDs de Step duplicados: {duplicates}"
            )
        if not workflow.policy.stop_on_failure:
            raise WorkflowValidationException(
                "Política stop_on_failure=false ainda não é suportada."
            )
        return workflow
