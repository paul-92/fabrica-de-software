# ADR-025 — Planejamento determinístico antes da execução

**Status:** aceito  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

Workflow e Agent Runtime executavam trabalho sem um contrato canônico que
explicasse previamente objetivo, passos, dependências, capabilities e
estimativas.

## Decisão

Criar uma porta `Planner` e um `PlanningEngine` isolado, determinístico e
baseado em regras. O motor consulta opcionalmente `AgentMemory` e
`ToolRegistry`, constrói um `ExecutionPlan`, valida-o e emite observabilidade.
Ele não executa Tools nem agentes.

WorkflowEngine e AgentExecutionService dependem apenas da porta opcional e
solicitam o plano antes da execução. A ausência de Planner preserva a API e o
comportamento anteriores.

## Consequências

- planos equivalentes possuem a mesma identidade;
- falhas de planejamento impedem o início do trabalho;
- estratégias e infraestrutura são substituíveis por injeção;
- Timeline e métricas distinguem planejamento de execução;
- não há autonomia, LLM, replanejamento ou persistência nesta decisão.

## Evidência

`src/asep/planning/`, `tests/test_planning_engine.py` e
`tests/test_planning_integration.py`.
