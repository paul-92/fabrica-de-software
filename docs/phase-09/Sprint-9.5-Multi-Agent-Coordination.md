# Sprint 9.5 — Multi-Agent Coordination

**Dono:** Engenharia ASEP | **Status:** implementada localmente  
**Data:** 2026-07-30

## Objetivo

Criar a infraestrutura oficial, determinística e orientada por contratos para
distribuir um ExecutionPlan entre agentes especializados.

## Entregas

- AgentCoordinator e porta Coordinator;
- AgentAssignment e CoordinationContext/Result;
- resolução por capability e política de seleção;
- fila lógica sequencial dependency-aware;
- agregador determinístico;
- política, validação e exceções específicas;
- Timeline e métricas;
- integração opcional com Planning, Runtime, Workflow e Memory.

## Lifecycle

```text
Workflow -> PlanningEngine -> ExecutionPlan
                            -> AgentCoordinator
                            -> Assignments/Queue
                            -> AgentRuntime
                            -> ResultAggregator
                            -> Workflow
```

Eventos: `coordination_started`, `agent_selected`, `assignment_created`,
`assignment_completed`, `coordination_completed` e `coordination_failed`.

Métricas: planos coordenados, assignments, duração, falhas e duração de
agregação.

## Limites

Execução sequencial, local e síncrona. Timeout é apenas lógico e delegado ao
Runtime. Não há LLM, scheduler, rede, paralelismo ou Knowledge Graph.

## Evidência

Código em `src/asep/agents/coordination/`; testes em
`tests/test_agent_coordination.py`; decisão em
[ADR-026](../adr/ADR-026-multi-agent-coordination.md).
