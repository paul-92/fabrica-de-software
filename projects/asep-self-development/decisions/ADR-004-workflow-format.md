# ADR-004 — Formato declarativo de workflows

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
Workflows já existem em YAML e o MVP é sequencial.
## Problema
Executar definições de forma previsível e compatível com evolução.
## Alternativas
Código Python; YAML livre; YAML com schema/modelos versionados; DSL própria.
## Decisão
YAML carregado com `safe_load`, validado por Pydantic estrito, com `version`,
stages, dependencies, agents, conditions, gates, artifacts e failure handling.
## Justificativa
Preserva declaratividade e evita parser/DSL novos.
## Consequências
Engine recebe modelos, não dicionários. Campos desconhecidos falham. Breaking
change exige nova versão/migração.
## Riscos
Workflow corporativo contém paralelismo fora do MVP. Criar tailoring/workflow 0.1
sequencial aprovado; não executar `parallel` silenciosamente.
