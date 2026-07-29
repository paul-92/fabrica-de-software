"""Erros de domínio da construção de grafos de execução."""

from asep.errors import AsepError


class ExecutionGraphError(AsepError):
    code = "EXECUTION_GRAPH_ERROR"
    category = "validation"
    next_action = "Corrija o workflow, estado ou relatórios informados."
    exit_code = 3


class InvalidGraphError(ExecutionGraphError):
    code = "EXECUTION_GRAPH_INVALID"
