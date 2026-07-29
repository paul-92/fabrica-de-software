"""Erros específicos de exportação textual."""

from asep.errors import AsepError


class MermaidExportError(AsepError):
    code = "MERMAID_EXPORT_ERROR"
    category = "validation"
    next_action = "Verifique o ExecutionGraph e o EdgeType informado."
    exit_code = 3


class BpmnExportError(AsepError):
    code = "BPMN_EXPORT_ERROR"
    category = "validation"
    next_action = "Verifique se o ExecutionGraph é acíclico e suportado."
    exit_code = 3


class UnsupportedBpmnGraphError(BpmnExportError):
    code = "BPMN_GRAPH_UNSUPPORTED"
