"""Modelos imutáveis usados pela camada de prompting."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PromptContextItem(BaseModel):
    """Item nomeado de contexto adicional."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    value: str


class PromptBuildInput(BaseModel):
    """Dados já preparados para construir uma tarefa textual de agente."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    workflow_id: str | None = None
    stage_id: str | None = None
    stage_name: str | None = None
    agent_id: str | None = None
    task: str | None = None
    stage_objective: str | None = None
    project_description: str | None = None
    agent_contract: str | None = None
    required_inputs: tuple[str, ...] = ()
    expected_artifacts: tuple[str, ...] = ()
    quality_criteria: tuple[str, ...] = ()
    restrictions: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    additional_context: tuple[PromptContextItem, ...] = ()
    response_format: str | None = None


class PromptBuildResult(BaseModel):
    """Prompt final e metadados observáveis de sua construção."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt: str
    provider_neutral: bool
    included_sections: tuple[str, ...]
    warnings: tuple[str, ...] = ()
