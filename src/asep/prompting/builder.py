"""Builder determinístico de tarefas Markdown para agentes."""

from __future__ import annotations

from collections.abc import Iterable

from asep.prompting.models import PromptBuildInput, PromptBuildResult

DEFAULT_RESTRICTIONS = (
    "Não alterar arquivos fora do escopo autorizado.",
    "Não fazer commit.",
    "Não fazer push.",
    "Executar os testes indicados.",
    "Informar os arquivos modificados.",
    "Relatar falhas e pendências.",
)

DEFAULT_RESPONSE_FORMAT = (
    "Apresente um resumo do trabalho, os arquivos modificados, os testes "
    "executados e seus resultados, além de falhas ou pendências."
)


class PromptBuilder:
    """Transforma dados preparados em um prompt Markdown provider-neutral."""

    def build(self, data: PromptBuildInput) -> PromptBuildResult:
        sections: list[tuple[str, str]] = []
        warnings = self._warnings(data)

        task = data.task or self._default_task(data)
        self._append(sections, "tarefa", "# Tarefa", task)

        identification = self._identification(data)
        self._append(
            sections,
            "identificação da execução",
            "## Identificação da execução",
            identification,
        )
        self._append(
            sections,
            "objetivo",
            "## Objetivo",
            data.stage_objective,
        )

        project_context = self._project_context(data)
        self._append(
            sections,
            "contexto do projeto",
            "## Contexto do projeto",
            project_context,
        )
        self._append(
            sections,
            "responsabilidade do agente",
            "## Responsabilidade do agente",
            data.agent_contract,
        )
        self._append_list(
            sections,
            "entradas",
            "## Entradas",
            data.required_inputs,
            preserve_order=True,
        )
        self._append_list(
            sections,
            "saídas esperadas",
            "## Saídas esperadas",
            data.expected_artifacts,
        )
        self._append_list(
            sections,
            "critérios de qualidade",
            "## Critérios de qualidade",
            data.quality_criteria,
        )
        self._append_list(
            sections,
            "restrições",
            "## Restrições",
            (*DEFAULT_RESTRICTIONS, *data.restrictions),
        )
        self._append_list(
            sections,
            "perguntas ou pendências",
            "## Perguntas ou pendências",
            data.open_questions,
        )
        self._append(
            sections,
            "formato esperado da resposta",
            "## Formato esperado da resposta",
            data.response_format or DEFAULT_RESPONSE_FORMAT,
        )

        return PromptBuildResult(
            prompt="\n\n".join(content for _, content in sections) + "\n",
            provider_neutral=True,
            included_sections=tuple(name for name, _ in sections),
            warnings=warnings,
        )

    @staticmethod
    def _append(
        sections: list[tuple[str, str]],
        name: str,
        heading: str,
        content: str | None,
    ) -> None:
        if content and content.strip():
            sections.append((name, f"{heading}\n\n{content.strip()}"))

    def _append_list(
        self,
        sections: list[tuple[str, str]],
        name: str,
        heading: str,
        values: Iterable[str],
        *,
        preserve_order: bool = False,
    ) -> None:
        normalized = tuple(value.strip() for value in values if value.strip())
        if not normalized:
            return
        ordered = (
            normalized
            if preserve_order
            else self._sorted_unique(normalized)
        )
        content = "\n".join(f"- {value}" for value in ordered)
        sections.append((name, f"{heading}\n\n{content}"))

    @staticmethod
    def _sorted_unique(values: Iterable[str]) -> tuple[str, ...]:
        unique = dict.fromkeys(values)
        return tuple(sorted(unique, key=lambda value: (value.casefold(), value)))

    @staticmethod
    def _default_task(data: PromptBuildInput) -> str:
        stage = data.stage_name or data.stage_id
        if stage:
            return f"Executar a etapa {stage} conforme o contexto fornecido."
        return "Executar a tarefa conforme o contexto fornecido."

    @staticmethod
    def _identification(data: PromptBuildInput) -> str | None:
        fields = (
            ("Run ID", data.run_id),
            ("Projeto", data.project_id),
            ("Nome do projeto", data.project_name),
            ("Workflow", data.workflow_id),
            ("Etapa", data.stage_id),
            ("Nome da etapa", data.stage_name),
            ("Agente", data.agent_id),
        )
        lines = [f"- {label}: `{value}`" for label, value in fields if value]
        return "\n".join(lines) or None

    def _project_context(self, data: PromptBuildInput) -> str | None:
        paragraphs: list[str] = []
        if data.project_description and data.project_description.strip():
            paragraphs.append(data.project_description.strip())
        context_items = sorted(
            data.additional_context,
            key=lambda item: (item.name.casefold(), item.name, item.value),
        )
        if context_items:
            paragraphs.extend(
                f"- {item.name.strip()}: {item.value.strip()}"
                for item in context_items
                if item.name.strip() and item.value.strip()
            )
        return "\n".join(paragraphs) or None

    @staticmethod
    def _warnings(data: PromptBuildInput) -> tuple[str, ...]:
        checks = (
            (data.run_id, "run_id não informado."),
            (data.project_id, "project_id não informado."),
            (data.workflow_id, "workflow_id não informado."),
            (data.stage_id, "stage_id não informado."),
            (data.agent_id, "agent_id não informado."),
            (data.stage_objective, "objetivo da etapa não informado."),
            (data.agent_contract, "contrato do agente não informado."),
            (data.required_inputs, "entradas requeridas não informadas."),
            (data.expected_artifacts, "artefatos esperados não informados."),
            (data.quality_criteria, "critérios de qualidade não informados."),
        )
        return tuple(message for value, message in checks if not value)
