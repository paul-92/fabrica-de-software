"""Exceções específicas da coordenação determinística de agentes."""


class CoordinationError(Exception):
    """Falha base da coordenação."""


class AgentAssignmentError(CoordinationError):
    """Uma atribuição não pôde ser criada ou validada."""


class CapabilityResolutionError(CoordinationError):
    """Nenhum agente elegível foi encontrado para uma capability."""


class CoordinationValidationError(CoordinationError):
    """Contexto, plano ou política de coordenação inválidos."""


class ResultAggregationError(CoordinationError):
    """Resultados individuais não formam uma consolidação válida."""


__all__ = [
    "AgentAssignmentError",
    "CapabilityResolutionError",
    "CoordinationError",
    "CoordinationValidationError",
    "ResultAggregationError",
]
