# ADR-024 — Memória operacional separada do Agent Runtime

**Status:** aceita localmente  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

Agentes precisam reutilizar contexto entre execuções. Persistir, filtrar,
expirar, pesquisar e limitar esse conteúdo dentro do Runtime misturaria
lifecycle de execução com armazenamento e segurança.

## Decisão

Criar `MemoryStore` como porta de persistência, `MemoryService` como caso de uso
e `ContextBuilder` como composição do payload. O Agent Runtime depende somente
de `ContextProvider`.

- Memory não conhece providers, Workflow Engine ou Tool Registry;
- `RepositoryFactory` seleciona Store;
- SQLite reutiliza `SQLiteDatabase`;
- retenção é explícita e determinística;
- filtragem ocorre antes da persistência;
- contexto é limitado e serializável;
- API permanece síncrona.

## Por que ContextBuilder existe

Recuperar memória e montar input são responsabilidades diferentes. O builder
combina workflow, metadata e entradas relevantes, aplica limite e registra
duração sem transformar Runtime ou Store em formatadores.

## Preparação para memória vetorial

Consumidores dependem da porta `MemoryStore` e de consultas de domínio.
Implementações futuras podem substituir o mecanismo de busca sem alterar
Runtime, Workflow ou `MemoryService`. Não foram adicionados embeddings, scores
ou tipos de fornecedor antes de existir requisito.

## Alternativas consideradas

1. **Guardar contexto no Runtime:** rejeitada por acoplamento e baixa
   testabilidade.
2. **Persistir somente no WorkflowContext:** rejeitada porque não sobrevive ao
   processo e mistura estado executável com memória.
3. **Usar banco vetorial agora:** rejeitada por ausência de busca semântica
   autorizada.
4. **Sem retenção:** rejeitada por crescimento ilimitado e risco de dados
   obsoletos.
5. **Um Store JSON novo:** adiado; a Sprint exige memória e SQLite.

## Consequências

Positivas:

- persistência substituível e auditável;
- segurança central antes da escrita;
- contexto pequeno e determinístico;
- evolução vetorial possível por adapter.

Custos:

- mais uma tabela no schema SQLite;
- backend file não possui durabilidade de memória;
- filtro textual possui limites;
- retenção e métricas são síncronas/locais.

## Evidência

Código em `src/asep/memory/`; testes de Store, Service e integração. Referência:
[Agent Memory](../agents/AgentMemory.md).

