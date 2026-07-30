# Sprint 9.3 — Agent Memory & Context Management

**Público:** engenharia, arquitetura e QA  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementada localmente

## Objetivo

Adicionar memória operacional persistente e contexto reutilizável, sem
embeddings, RAG, banco vetorial ou memória inteligente.

## Entregas

- modelos, categorias, importância e consulta;
- contratos `AgentMemory`, `MemoryStore`, `MemoryRepository` e
  `ContextProvider`;
- stores em memória e SQLite;
- `MemoryService`, `MemoryFilter`, retenção e expiração;
- `ContextBuilder`;
- Timeline e métricas;
- Factory com Store por backend;
- Agent Runtime e Workflow integrados por portas;
- testes, documentação e ADR-024.

## Fluxo

```text
Workflow -> Agent Runtime -> ContextProvider -> ContextBuilder
                                              -> MemoryService
                                              -> MemoryStore
                         -> ToolExecutor
                         -> Agent
```

Memory não conhece Workflow Engine, Tool Registry ou providers.

## Evidências

Testes cobrem contratos, CRUD compartilhado, persistência SQLite entre
instâncias, índices, consulta, filtragem, expiração, retenção, contexto,
performance básica, Factory, Runtime, Workflow, Timeline e métricas.

## Riscos e limitações

- backend `file` usa Store volátil;
- filtro não detecta segredos sem marcador;
- contexto usa prioridade/recência, não relevância semântica;
- métricas são locais;
- sem concorrência avançada, compressão ou busca vetorial;
- 4.062 temporários da Sprint 9.1 continuam rastreados no commit anterior e
  deletados no worktree.

## Checklist

- [x] contratos, stores, service, builder, filtro e policy;
- [x] SQLite, Factory, Runtime e Workflow;
- [x] Timeline, métricas e testes;
- [x] documentação e ADR;
- [ ] saneamento Git e commit autorizados.

## Próxima ação

Responsável: mantenedor autorizado. Gatilho: gates técnicos verdes e decisão
sobre temporários rastreados. A Sprint 9.4 não foi iniciada.

## Referências

[Agent Memory](../agents/AgentMemory.md),
[ContextBuilder](../agents/ContextBuilder.md) e
[ADR-024](../adr/ADR-024-agent-memory.md).

