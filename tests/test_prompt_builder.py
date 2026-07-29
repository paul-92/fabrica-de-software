import pytest
from pydantic import ValidationError

from asep.prompting import (
    PromptBuildInput,
    PromptBuilder,
    PromptContextItem,
)


def complete_input() -> PromptBuildInput:
    return PromptBuildInput(
        run_id="f2f1a9f1-2c60-4fa0-9120-6b9197589488",
        project_id="asep",
        project_name="ASEP",
        workflow_id="software-project",
        stage_id="analysis",
        stage_name="Business Analysis",
        agent_id="business-analyst",
        task="Analisar os requisitos confirmados do projeto.",
        stage_objective="Produzir requisitos rastreáveis.",
        project_description="Plataforma local de engenharia de software.",
        agent_contract="Analisar sem inventar requisitos ou evidências.",
        required_inputs=("brief", "escopo aprovado"),
        expected_artifacts=("requirements.md", "risks.md"),
        quality_criteria=("Rastreabilidade", "Clareza"),
        restrictions=("Preservar dados internos.",),
        open_questions=("Quem aprova o escopo?",),
        additional_context=(
            PromptContextItem(name="Prioridade", value="Alta"),
            PromptContextItem(name="Idioma", value="Português"),
        ),
        response_format="Entregue Markdown e um resumo das validações.",
    )


def test_builds_structured_prompt_with_complete_context() -> None:
    result = PromptBuilder().build(complete_input())

    assert result.provider_neutral is True
    assert result.warnings == ()
    assert result.included_sections == (
        "tarefa",
        "identificação da execução",
        "objetivo",
        "contexto do projeto",
        "responsabilidade do agente",
        "entradas",
        "saídas esperadas",
        "critérios de qualidade",
        "restrições",
        "perguntas ou pendências",
        "formato esperado da resposta",
    )
    assert "# Tarefa" in result.prompt
    assert "## Identificação da execução" in result.prompt
    assert "## Responsabilidade do agente" in result.prompt
    assert "## Formato esperado da resposta" in result.prompt
    assert "f2f1a9f1-2c60-4fa0-9120-6b9197589488" in result.prompt


def test_omits_empty_optional_sections_and_returns_warnings() -> None:
    result = PromptBuilder().build(
        PromptBuildInput(task="Executar validação local.")
    )

    assert "## Objetivo" not in result.prompt
    assert "## Contexto do projeto" not in result.prompt
    assert "## Responsabilidade do agente" not in result.prompt
    assert "## Entradas" not in result.prompt
    assert "## Saídas esperadas" not in result.prompt
    assert "## Critérios de qualidade" not in result.prompt
    assert "## Perguntas ou pendências" not in result.prompt
    assert "## Restrições" in result.prompt
    assert "## Formato esperado da resposta" in result.prompt
    assert "run_id não informado." in result.warnings
    assert "objetivo da etapa não informado." in result.warnings
    assert "contrato do agente não informado." in result.warnings


def test_same_input_produces_identical_result() -> None:
    builder = PromptBuilder()
    data = complete_input()

    first = builder.build(data)
    second = builder.build(data)

    assert first == second
    assert "2026-" not in first.prompt


def test_sorts_collections_without_semantic_order_and_context_keys() -> None:
    data = complete_input().model_copy(
        update={
            "expected_artifacts": ("zeta.md", "alpha.md", "zeta.md"),
            "quality_criteria": ("Segurança", "Clareza"),
            "open_questions": ("Questão Z", "Questão A"),
            "additional_context": (
                PromptContextItem(name="Zeta", value="2"),
                PromptContextItem(name="Alfa", value="1"),
            ),
        }
    )

    prompt = PromptBuilder().build(data).prompt

    assert prompt.index("alpha.md") < prompt.index("zeta.md")
    assert prompt.count("zeta.md") == 1
    assert prompt.index("Clareza") < prompt.index("Segurança")
    assert prompt.index("Questão A") < prompt.index("Questão Z")
    assert prompt.index("Alfa: 1") < prompt.index("Zeta: 2")


def test_preserves_required_input_order() -> None:
    data = complete_input().model_copy(
        update={"required_inputs": ("terceiro", "primeiro", "segundo")}
    )

    prompt = PromptBuilder().build(data).prompt

    assert prompt.index("- terceiro") < prompt.index("- primeiro")
    assert prompt.index("- primeiro") < prompt.index("- segundo")


def test_includes_safe_default_restrictions_with_explicit_restrictions() -> None:
    prompt = PromptBuilder().build(complete_input()).prompt

    assert "Não fazer commit." in prompt
    assert "Não fazer push." in prompt
    assert "Não alterar arquivos fora do escopo autorizado." in prompt
    assert "Informar os arquivos modificados." in prompt
    assert "Executar os testes indicados." in prompt
    assert "Relatar falhas e pendências." in prompt
    assert "Preservar dados internos." in prompt


def test_supports_unicode_and_portuguese_content() -> None:
    data = complete_input().model_copy(
        update={
            "task": "Revisar autenticação, privacidade e ações críticas.",
            "project_description": "Solução para São Paulo com conteúdo em português.",
            "required_inputs": ("visão do usuário", "restrições de negócio"),
        }
    )

    prompt = PromptBuilder().build(data).prompt

    assert "autenticação, privacidade e ações críticas" in prompt
    assert "São Paulo" in prompt
    assert "restrições de negócio" in prompt


def test_template_has_no_provider_specific_references() -> None:
    prompt = PromptBuilder().build(complete_input()).prompt.casefold()

    assert "codex" not in prompt
    assert "claude code" not in prompt


def test_input_model_is_frozen_and_rejects_unknown_fields() -> None:
    data = complete_input()

    with pytest.raises(ValidationError, match="frozen_instance"):
        data.task = "Outra tarefa"

    with pytest.raises(ValidationError, match="extra_forbidden"):
        PromptBuildInput(unexpected="value")
