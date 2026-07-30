# Dependências do Workflow Orchestrator

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Visão Geral

Mapa da fronteira do coordenador genérico.

## O Problema

Acoplar Steps a backends, Metrics ou API impediria simulação e substituição.

## A Solução

Injetar somente portas de persistência e manter projeções analíticas fora.

## Explicação simples

O maestro conhece músicos e partitura, não a fábrica dos instrumentos.

## Explicação técnica

```text
composition -> WorkflowOrchestrator -> RunRepository
                                   `-> TimelineRepository/Recorder
WorkflowOrchestrator -> workflow models
WorkflowOrchestrator -> WorkflowEngine -> Validator/Executor
WorkflowEngine -> WorkflowStep <- AgentStepAdapter -> Agent
Composition -> AgentRegistry -> Agent
WorkflowOrchestrator -> WorkflowPersistenceService -> WorkflowRepository
Metrics/Dashboard -> RunQueryService -> repositories
```

## Componentes

Workflow, Steps, contexto, repositories, Timeline, Query, Metrics e API.

## Fluxo completo

Composição injeta portas; serviço coordena; consumidores leem projeções.

## Dependências

Proibidos dentro do serviço: implementations concretas, Factory, Metrics,
Dashboard, provider, agente concreto e Orchestrator legado. Agentes entram
como `WorkflowStep` por adapter, sem import no Engine.

O Registry também permanece fora do Engine. A composição recupera o agente e
constrói o adapter.

O Engine também não conhece persistência. O Orchestrator injeta a porta do
serviço após obter o resultado terminal.

## Exemplos

Testes injetam repositories em memória; integração repete com file/sqlite.

## Testes

Teste parametrizado comprova os três backends sem mudança do serviço.

## Erros comuns

Injetar `MetricsService` para “registrar” métricas é incorreto: ele é read-only.

## Limitações

Fronteiras são verificadas por revisão/testes, não ferramenta estática.

## Evolução futura

Automatizar regras de imports quando a camada crescer.

## Referências

[Workflow Orchestrator](WorkflowOrchestrator.md).

## Relacionado a

Sprint 8.1; Fase 08; ADR-017; testes; Architecture e Glossário.
