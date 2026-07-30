# Agent Coordinator

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

## Objetivo

Distribuir um `ExecutionPlan` entre agentes registrados e consolidar os
resultados por contratos determinísticos. O Coordinator não executa Tools,
não resolve providers e não cria planos.

## Fluxo

```text
ExecutionPlan
  -> CoordinationValidator
  -> AgentCapabilityResolver
  -> AgentAssignment
  -> AgentExecutionQueue
  -> AgentRuntime
  -> ResultAggregator
  -> CoordinationResult
```

O `RegistryAgentCapabilityResolver` consulta exclusivamente o `AgentRegistry`.
Agente explícito, afinidade declarada e ordem estável do Registry formam a
seleção, sem heurística de IA. Cada assignment possui identidade determinística
derivada do plano, etapa e agente.

A fila respeita dependências e prioridade e nesta versão é exclusivamente
sequencial. Falha pode interromper a fila conforme a política; assignments
restantes tornam-se `skipped`.

## Integrações

- Planning: `CoordinationContext` recebe o `ExecutionPlan`;
- Runtime: toda execução passa pela porta `AgentRuntime`;
- Memory: entradas são serializadas no input da execução;
- Workflow: `WorkflowEngine` aceita Coordinator opcional após o Planner;
- Timeline e métricas registram o lifecycle sem conteúdo sensível.

## Limitações

Sem paralelismo, scheduler, rede, timeout interruptivo, LLM, replanejamento ou
execução direta de Tools.

Veja [Coordination Policies](CoordinationPolicies.md),
[Sprint 9.5](../phase-09/Sprint-9.5-Multi-Agent-Coordination.md) e
[ADR-026](../adr/ADR-026-multi-agent-coordination.md).
