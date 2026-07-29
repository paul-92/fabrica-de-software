# Handoff — Business Analysis para Software Architecture

**ID:** HND-BA-ARCH-001  
**Data:** 2026-07-28  
**De:** Business Analyst  
**Para:** Software Architect  
**Status:** ready  
**Gate anterior:** `QG-ANALYSIS` approved

## Contexto e objetivo

Projetar a arquitetura da primeira versão executável da ASEP via CLI, dentro do
escopo e stack aprovados, sem implementar código.

## Entradas validadas

- [requisitos](../business-analysis/requirements.md);
- [requisitos funcionais](../business-analysis/functional-requirements.md);
- [requisitos não funcionais](../business-analysis/non-functional-requirements.md);
- [regras de negócio](../business-analysis/business-rules.md);
- [escopo](../business-analysis/scope.md);
- [MVP](../business-analysis/mvp.md);
- [hipóteses](../business-analysis/assumptions.md);
- [restrições](../business-analysis/constraints.md);
- [dependências](../business-analysis/dependencies.md);
- [riscos](../business-analysis/risks.md);
- [critérios de aceite](../business-analysis/acceptance-criteria.md);
- [decisão da stack](../decisions/DEC-STACK-001-approved-stack.md);
- [review do gate](../reports/business-analysis-review.md).

## Decisões tomadas

- versão `0.1` executável via CLI;
- MVP: Registry, Workflow Engine, Runtime, Orchestrator, Business Analyst,
  Markdown, Logging e Quality Gates;
- stack conforme ADR-001;
- itens fora do MVP conforme `scope.md`.

## Pendências e riscos

Personas, ambientes suportados, targets de capacidade/retenção, Security e
Quality Lead permanecem abertos. Esses itens devem ser tratados como lacunas,
restrições ou riscos; não podem ser inventados.

## Trabalho esperado do Software Architect

Comparar alternativas internas à stack, definir componentes e fronteiras, estado
em arquivos, schemas, fluxo CLI, falhas, auditoria e testabilidade; produzir
documento de arquitetura e ADRs. Não implementar código.

## Critério de aceite do handoff

O Software Architect confirma required inputs, registra lacunas e inicia a etapa
`architecture` sem alterar escopo ou stack sem change request aprovado.
