# Sprint 9.4 — Planning Engine

**Dono:** Engenharia ASEP | **Status:** implementada localmente  
**Data:** 2026-07-30

## Objetivo e escopo

Introduzir planejamento canônico, determinístico e anterior à execução, sem
LLM e sem executar Tools. Foram entregues modelos imutáveis, estratégia
sequencial, políticas, validação, métricas, Timeline e integração opcional com
WorkflowEngine e AgentExecutionService.

## Arquitetura

```text
Goal + Context + Memory + Tools + Workflow
                  |
                  v
          PlanningEngine
      Strategy -> Validator
                  |
                  v
       PlanningResult/ExecutionPlan
                  |
         Workflow ou Agent Runtime
```

## Critérios demonstrados

- plano tipado e serializável;
- identidade e ordenação determinísticas;
- dependências, ciclos, capabilities e workflow validados;
- política de passos, profundidade e custo;
- eventos e métricas de sucesso/falha;
- plano solicitado uma vez antes da execução;
- nenhuma Tool é executada pelo planner;
- integrações anteriores permanecem opcionais.

## Limites e riscos

Estimativas são regras declaradas, não previsões. Não há persistência,
replanejamento, paralelismo ou resolução distribuída. O branch possui mudanças
acumuladas e exclusões de temporários rastreados que exigem revisão humana
antes de commit.

## Evidência

Código em `src/asep/planning/`; testes em `tests/test_planning_engine.py` e
`tests/test_planning_integration.py`; decisão em
[ADR-025](../adr/ADR-025-planning-engine.md).
