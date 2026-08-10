"""Erros tipados e seguros apresentados pela ASEP."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError


def describe_validation_error(error: ValidationError) -> str:
    """Resume falhas de schema sem repetir valores potencialmente sensíveis."""
    details = []
    for item in error.errors(include_input=False, include_url=False):
        location = ".".join(str(part) for part in item["loc"]) or "<root>"
        details.append(f"{location}: {item['msg']} ({item['type']})")
    return "; ".join(details)


class AsepError(Exception):
    """Erro esperado da plataforma, adequado para apresentação ao operador."""

    code = "ASEP_ERROR"
    category = "internal"
    retryable = False
    next_action = "Consulte o log local e acione o responsável técnico."
    exit_code = 5

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        self.message = message
        self.path = path
        suffix = f" Arquivo: {path}" if path else ""
        super().__init__(f"{message}{suffix}")


class ProjectNotFoundError(AsepError):
    code = "PROJECT_NOT_FOUND"
    category = "validation"
    next_action = "Informe um diretório de projeto existente."
    exit_code = 2


class ProjectValidationError(AsepError):
    code = "PROJECT_INVALID"
    category = "validation"
    next_action = "Corrija o manifesto ou os arquivos obrigatórios do projeto."
    exit_code = 3


class ProjectSessionNotFoundError(AsepError):
    code = "PROJECT_SESSION_NOT_FOUND"
    category = "validation"
    exit_code = 2


class ProjectExecutionNotFoundError(AsepError):
    code = "PROJECT_EXECUTION_NOT_FOUND"
    category = "validation"
    exit_code = 2


class ProjectHistoryConflictError(AsepError):
    code = "PROJECT_HISTORY_CONFLICT"
    category = "conflict"
    exit_code = 6


class RegistryValidationError(AsepError):
    code = "REGISTRY_INVALID"
    category = "validation"
    next_action = "Corrija o catálogo ou a referência indicada."
    exit_code = 3


class WorkflowValidationError(AsepError):
    code = "WORKFLOW_INVALID"
    category = "validation"
    next_action = "Corrija o workflow e valide novamente."
    exit_code = 3


class ConfigurationError(AsepError):
    code = "CONFIGURATION_INVALID"
    category = "persistence"
    next_action = "Corrija a configuração ou a permissão do caminho indicado."
    exit_code = 5


class ConsistencyError(AsepError):
    code = "CONSISTENCY_ERROR"
    category = "conflict"
    next_action = "Reconcilie projeto, Registry e workflow antes de repetir."
    exit_code = 6


class UnsupportedCapabilityError(AsepError):
    code = "CAPABILITY_NOT_SUPPORTED"
    category = "blocked"
    next_action = "Selecione um workflow estritamente sequencial aprovado."
    exit_code = 4


class StateTransitionError(AsepError):
    code = "STATE_TRANSITION_INVALID"
    category = "conflict"
    next_action = "Verifique o estado persistido e a transição solicitada."
    exit_code = 6


class StatePersistenceError(AsepError):
    code = "STATE_PERSISTENCE_ERROR"
    category = "persistence"
    next_action = "Verifique integridade e permissões do diretório da execução."
    exit_code = 5


class RunNotFoundError(AsepError):
    code = "RUN_NOT_FOUND"
    category = "validation"
    next_action = "Informe um run_id existente neste workspace."
    exit_code = 2


class RunNotResumableError(AsepError):
    code = "RUN_NOT_RESUMABLE"
    category = "conflict"
    next_action = (
        "Use uma execução blocked/failed; awaiting_approval exige aprovação "
        "formal ainda não implementada."
    )
    exit_code = 6


class AgentNotFoundError(AsepError):
    code = "AGENT_NOT_FOUND"
    category = "validation"
    next_action = "Registre um agente executável para a etapa."
    exit_code = 3


class AgentContractError(AsepError):
    code = "AGENT_CONTRACT_INVALID"
    category = "validation"
    next_action = "Corrija o contrato do agente no Registry."
    exit_code = 3


class AgentExecutionError(AsepError):
    code = "AGENT_EXECUTION_FAILED"
    category = "execution"
    next_action = "Corrija a causa registrada antes de retomar."
    exit_code = 5


class AgentResultError(AsepError):
    code = "AGENT_RESULT_INVALID"
    category = "validation"
    next_action = "Corrija o adaptador para retornar um AgentResult válido."
    exit_code = 3


class ArtifactError(AsepError):
    code = "ARTIFACT_ERROR"
    category = "persistence"
    next_action = "Verifique nome, colisão e diretório autorizado do artefato."
    exit_code = 5
