"""Exceções da fachada e do pipeline E2E."""


class PipelineError(Exception):
    """Falha base do pipeline."""


class PipelineValidationError(PipelineError):
    """Composição ou GoalRequest inválidos."""


class PipelineExecutionError(PipelineError):
    """Execução integrada não pôde ser concluída."""


class WorkflowUnavailableError(PipelineValidationError):
    """Workflow necessário não está disponível."""


class PipelineComponentUnavailableError(PipelineValidationError):
    """Componente obrigatório não foi configurado."""


__all__ = [
    "PipelineComponentUnavailableError",
    "PipelineError",
    "PipelineExecutionError",
    "PipelineValidationError",
    "WorkflowUnavailableError",
]
