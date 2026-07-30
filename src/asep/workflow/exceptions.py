"""Exceções específicas do Workflow Engine."""


class WorkflowEngineException(Exception):
    """Base dos erros esperados pelo engine genérico."""


class WorkflowValidationException(WorkflowEngineException):
    pass


class WorkflowExecutionException(WorkflowEngineException):
    pass


class WorkflowCancelledException(WorkflowExecutionException):
    pass


class WorkflowStepException(WorkflowExecutionException):
    def __init__(self, step_id: str, cause: Exception) -> None:
        self.step_id = step_id
        self.cause = cause
        message = str(cause) or type(cause).__name__
        super().__init__(f"Step {step_id} falhou: {message}")
