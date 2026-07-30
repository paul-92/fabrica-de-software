# ADR-026 — Coordenação separada da execução de agentes

**Status:** aceito  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

O Planning Engine passou a produzir planos, mas não deveria executar trabalho.
O Agent Runtime executa uma solicitação individual, sem responsabilidade por
distribuir um plano entre agentes.

## Decisão

Introduzir `AgentCoordinator` entre `ExecutionPlan` e `AgentRuntime`.
Coordenação, seleção, fila e agregação são componentes separados. Cada etapa
torna-se um `AgentAssignment` imutável e rastreável. A seleção usa somente
AgentRegistry, capabilities e políticas explícitas.

O Coordinator executa sequencialmente pela porta do Runtime e nunca chama
Tools diretamente. WorkflowEngine recebe Coordinator opcional, preservando
compatibilidade.

## Por que Assignment

Assignment separa intenção do plano, identidade do agente e estado da
coordenação. Isso permite auditoria, retry ou filas paralelas futuras sem
alterar `PlanStep` nem `AgentExecutionRequest`.

## Alternativas consideradas

- colocar coordenação no Planning Engine: rejeitada por misturar decisão e
  execução;
- colocar fila no Agent Runtime: rejeitada por ampliar o contrato individual;
- executar agentes no WorkflowEngine: rejeitada por acoplá-lo ao Registry;
- paralelismo imediato: rejeitado por complexidade e ausência de requisito.

## Consequências

A infraestrutura fica preparada para outra implementação de fila ou scheduler,
mas a versão atual permanece local, síncrona e sequencial. Distribuição em
rede, timeout real e inteligência de seleção continuam fora do escopo.

## Evidência

`src/asep/agents/coordination/` e `tests/test_agent_coordination.py`.
