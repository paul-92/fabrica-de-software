"""Primeiro agente executável da ASEP, sem LLM ou rede."""

from __future__ import annotations

from datetime import UTC, datetime

from jinja2 import Environment, StrictUndefined

from asep.execution.models import (
    AgentContext,
    AgentResult,
    AgentResultStatus,
    ArtifactDraft,
)

TEMPLATE = """# Resumo de execução — Business Analysis

**Projeto:** {{ project_name }} (`{{ project_id }}`)
**Run ID:** `{{ run_id }}`
**Agente:** `{{ agent_id }}`
**Etapa:** `{{ stage_id }}`
**Data e hora:** {{ finished_at }}
**Status:** completed

## Objetivo recebido

{{ objective }}

## Escopo recebido

{{ scope_received }}

## Restrições identificadas
{% for item in constraints %}
- {{ item }}
{% else %}
- Nenhuma restrição adicional fornecida ao agente.
{% endfor %}

## Itens pendentes
{% for item in pending_items %}
- {{ item }}
{% else %}
- Nenhum item pendente informado no contexto.
{% endfor %}

> Artefato determinístico. Nenhum requisito foi inferido ou criado.
"""


class BusinessAnalystAgent:
    id = "business-analyst"

    def execute(self, context: AgentContext) -> AgentResult:
        finished_at = datetime.now(UTC)
        missing = [
            name
            for name, value in (
                ("objective", context.objective),
                ("scope_received", context.scope_received),
            )
            if not value or not value.strip()
        ]
        if missing:
            return AgentResult(
                status=AgentResultStatus.BLOCKED,
                agent_id=context.agent_id,
                stage_id=context.stage_id,
                run_id=context.run_id,
                started_at=context.started_at,
                finished_at=finished_at,
                errors=[f"Entradas obrigatórias ausentes: {', '.join(missing)}"],
                metadata={"missing_inputs": missing},
            )

        environment = Environment(
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )
        content = environment.from_string(TEMPLATE).render(
            **context.model_dump(mode="json"),
            finished_at=finished_at.isoformat(),
        )
        return AgentResult(
            status=AgentResultStatus.COMPLETED,
            agent_id=context.agent_id,
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=context.started_at,
            finished_at=finished_at,
            artifacts=[
                ArtifactDraft(
                    relative_path="business-analysis/execution-summary.md",
                    content=content,
                )
            ],
            messages=["Resumo determinístico de Business Analysis produzido."],
        )
