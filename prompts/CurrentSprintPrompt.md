# Prompt oficial da Sprint atual

**Sprint:** 10.1 — Project Analyzer
**Estado:** implementada localmente; validação e publicação pendentes

## Objetivo

Analisar projetos de software deterministicamente e produzir um modelo rico de
estrutura, tecnologias, arquitetura, dependências e estatísticas.

## Escopo entregue

- `asep.project_analysis` com Scanner e detectores;
- modelos Pydantic imutáveis e estritos;
- linguagens, frameworks, package managers e entrypoints;
- dependências diretas, arquitetura, módulos e estatísticas;
- documentação técnica e ADR-029.

## Evidência

- testes de projeto vazio, Python, Next.js, misto e entradas inválidas;
- cobertura específica do novo módulo superior a 95%;
- suíte completa e gates de compilação/Git.

## Restrições

- nenhum LLM, embedding, banco vetorial ou integração externa;
- nenhuma integração com Agent Runtime, Workflow ou Pipeline;
- nenhuma geração, revisão, refatoração ou documentação automática;
- nenhuma Sprint 10.2;
- nenhum commit, push ou tag automático.

## Limites

Heurísticas são evidências determinísticas e podem produzir falsos positivos
ou negativos. Dependências transitivas, monorepos semânticos e parsing AST
multilinguagem permanecem fora do escopo.

Referências:
[Project Analysis](../docs/project-analysis/Overview.md),
[ProjectAnalyzer](../docs/project-analysis/ProjectAnalyzer.md),
[ADR-029](../docs/adr/ADR-029-project-analyzer.md) e
[NEXT_STEPS](../project/NEXT_STEPS.md).
