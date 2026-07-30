# Memória operacional de agentes

**Público:** engenharia, arquitetura e segurança  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

## Visão Geral

Agent Memory preserva fatos, decisões, observações, planos, tarefas, erros e
resultados entre execuções sem IA, embeddings ou busca vetorial.

```text
MemoryService -> MemoryStore
                 /       \
           InMemory      SQLite
```

## Contratos

- `MemoryId`, `MemoryEntry`, `MemoryCategory` e `MemoryImportance`;
- `MemoryStore`/`MemoryRepository`;
- `MemoryService` e `AgentMemory`;
- `MemoryQuery`, `MemoryFilter` e `MemoryRetentionPolicy`.

Entradas são imutáveis, timezone-aware e serializáveis. Pesquisa é
determinística por agente, categoria, texto, execução, workflow e metadata.

## Persistência

`InMemoryMemoryStore` isola estado por instância. `SQLiteMemoryStore` usa
`SQLiteDatabase`, a conexão e o schema compartilhados da ASEP. A tabela
`memory_entries` guarda colunas de consulta e payload JSON completo, com
índices por agente, execução e workflow.

`RepositoryFactory` entrega Store em memória nos backends `memory` e `file`, e
Store persistente no backend `sqlite`. Um backend JSON de memória não foi
autorizado nesta Sprint.

## Retenção e expiração

A política define:

- máximo de entradas por agente;
- expiração padrão opcional;
- tamanho máximo do contexto;
- remoção de expirados;
- preferência por remover baixa prioridade;
- flag reservada para compressão futura.

Compressão inteligente não é executada. Quando há excesso, as entradas menos
importantes e mais antigas são removidas de modo determinístico.

## Segurança

Antes da persistência, `MemoryFilter` remove metadata sensível e redige pares
`chave=valor` ou `chave: valor` no conteúdo. São tratados password, secret,
token, authorization, api key, private key, bearer, cookies e credentials.
Timeline recebe somente IDs, categoria e importância.

Filtragem baseada em chaves não consegue reconhecer um segredo sem qualquer
marcador semântico; chamadores continuam responsáveis por classificar dados.

## Observabilidade

Eventos: saved, loaded, updated, deleted, expired e filtered. Métricas:
entradas, leituras, escritas, updates, deletes, hits, misses e duração de
construção de contexto.

## Evolução vetorial

Consumidores dependem de `MemoryStore` e `MemoryQuery`, não de SQLite. Um Store
vetorial futuro pode implementar a mesma porta ou uma extensão compatível,
mantendo `MemoryService`, Runtime e Workflow independentes. Nenhum embedding,
score vetorial ou dependência de IA foi antecipado.

## Referências

[ContextBuilder](ContextBuilder.md),
[Sprint 9.3](../phase-09/Sprint-9.3-Agent-Memory.md) e
[ADR-024](../adr/ADR-024-agent-memory.md).

