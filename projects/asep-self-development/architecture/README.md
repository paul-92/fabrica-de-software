# ASEP Self-development — Architecture

**Status:** aprovado pelo Product Owner em 2026-07-28  
**Gate anterior:** `QG-ANALYSIS` approved

## Finalidade

Registrar opções, arquitetura e ADRs da versão 0.1. A stack está aprovada em
[`DEC-STACK-001`](../decisions/DEC-STACK-001-approved-stack.md); o desenho interno permanece
aberto.

## Entrada atual

- [handoff da Business Analysis](handoff-from-business-analysis.md);
- [baseline de requisitos](../business-analysis/requirements.md);
- [riscos](../business-analysis/risks.md);
- [critérios de aceite](../business-analysis/acceptance-criteria.md).

## Artefatos

- [visão geral](architecture-overview.md), [contexto](system-context.md) e
  [componentes](component-model.md);
- [responsabilidades](module-responsibilities.md), [fluxo](execution-flow.md),
  [estado](state-model.md) e [dados](data-model.md);
- designs de [Registry](registry-design.md), [Workflow Engine](workflow-engine-design.md),
  [Runtime](runtime-design.md), [Orchestrator](orchestrator-design.md) e [CLI](cli-design.md);
- [artefatos](artifact-management.md), [logging/audit](logging-and-audit.md),
  [erros](error-handling.md), [segurança](security-baseline.md) e
  [observabilidade](observability-design.md);
- [testes](testing-strategy.md), [deployment](deployment-model.md),
  [riscos](technical-risks.md), [roadmap](technical-roadmap.md),
  [rastreabilidade](traceability-matrix.md) e [perguntas](open-technical-questions.md);
- [catálogo de ADRs](architecture-decisions.md);
- [review](../reports/architecture-review.md).

## Condição de uso

Cada novo artefato identifica fonte, dono, status e relação com o workflow
`software-project`. Itens sem confirmação permanecem como pergunta ou hipótese.

## Limite atual

Esta pasta não autoriza código, gasto, publicação ou uso de dados reais. Planning
aguarda aprovação da Arquitetura pelo Product Owner. Mudança de stack ou escopo
exige change request.
