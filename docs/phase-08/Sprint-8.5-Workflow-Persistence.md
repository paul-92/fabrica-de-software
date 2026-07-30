# Sprint 8.5 — Workflow Persistence

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída localmente

## Visão Geral

Persistência especializada do resultado completo de workflows em memória,
arquivo JSON ou SQLite.

## O Problema

Runs e Timeline eram persistíveis, mas a definição e o resultado consolidado do
workflow permaneciam transitórios.

## A Solução

`WorkflowPersistenceService` transforma definição e resultado em
`WorkflowSnapshot`. A porta `WorkflowRepository` possui três implementações
selecionadas pela `RepositoryFactory`.

## Explicação simples

Além do recibo da execução e do diário de eventos, a ASEP agora guarda uma
fotografia completa do roteiro executado.

## Arquitetura

```text
WorkflowOrchestrator -> WorkflowPersistenceService -> WorkflowRepository
                                                    /       |       \
                                               memory      file    sqlite

WorkflowEngine -------------------------------- sem backend
```

## WorkflowSnapshot

O snapshot contém identidade própria, `workflow_id`, `run_id`, versão, nome,
descrição, status, timestamps, duração, Steps executadas e pendentes, agente
opcional, IDs da Timeline, métricas e metadados JSON.

Ele é frozen, estrito e não guarda `WorkflowContext`, Steps ou exceções Python.

## Operações

- `save` preserva um novo snapshot e rejeita ID duplicado;
- `update` altera somente um snapshot existente;
- `get`, `exists` e `list`;
- consultas por status, Run, Workflow e período inclusivo;
- listagens ordenadas por `started_at` e ID.

O histórico entre runs e versões é preservado por `snapshot.id`: múltiplos
snapshots podem referenciar o mesmo Workflow ou Run.

## Integração

O Orchestrator aceita uma porta opcional e persiste o resultado somente após
adicionar os eventos externos de início/fim. Sem injeção, mantém o comportamento
anterior. A Factory entrega os três repositories no mesmo bundle.

Configuração file:

```text
ASEP_WORKFLOWS_FILENAME=workflow-snapshots.json
```

SQLite cria `workflow_snapshots` e índices para workflow, run e status.

## Testes

Testes compartilhados exercitam os três backends, serialização, validações,
histórico, consultas, persistência entre instâncias, serviço, Factory,
configuração e integração com Orchestrator, Timeline e Metrics.

## Limitações

- não há retomada ou reconstrução de objetos vivos;
- não há persistência de agentes;
- não há eventos, filas, distribuição ou sincronização;
- update não cria revisão automática: histórico exige novo `snapshot.id`;
- Dashboard API não expõe snapshots nesta Sprint.

## Referências

[Workflow Persistence](../workflows/WorkflowPersistence.md) e
[ADR-021](../adr/ADR-021-workflow-snapshot-persistence.md).

