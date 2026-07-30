# Planning Engine

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

## Objetivo

Transformar objetivo, contexto, memória, capabilities, Tools e workflow em um
plano validado antes da execução. O motor é síncrono, determinístico e baseado
em regras; ele nunca executa Agent, Tool ou WorkflowStep.

## Fluxo

```text
PlanningRequest
  -> enriquecimento opcional por AgentMemory e ToolRegistry
  -> PlanningStrategy
  -> ExecutionPlan
  -> PlanningValidator
  -> PlanningResult + Timeline + métricas
```

`PlanningEngine` recebe todas as dependências por injeção. A estratégia padrão
preserva a ordem declarada no workflow e cria dependências sequenciais quando
elas não são explícitas. O identificador do plano é derivado de uma
representação JSON canônica; timestamps não participam dessa identidade.

## Integração

`WorkflowEngine` e `AgentExecutionService` aceitam opcionalmente a porta
`Planner`. Quando configurada, a execução só começa após um plano válido. O
plano serializável é colocado no contexto da execução e é criado uma única vez.

## Falhas e observabilidade

Planos vazios, ciclos, dependências ou capabilities inexistentes, limites de
profundidade/custo e divergência do workflow são rejeitados. Timeline registra
`planning_requested`, `planning_started`, `plan_validated`,
`planning_completed`, `plan_rejected` ou `planning_failed`. Métricas locais
registram quantidade, duração, falhas e média de passos.

## Limites

Não há LLM, replanejamento, paralelismo real, execução de Tools, persistência de
planos ou otimização. Essas capacidades exigem requisitos próprios.

Veja [ExecutionPlan](ExecutionPlan.md), [ADR-025](../adr/ADR-025-planning-engine.md)
e [Sprint 9.4](../phase-09/Sprint-9.4-Planning-Engine.md).
