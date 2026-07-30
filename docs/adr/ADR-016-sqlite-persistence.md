# ADR-016 — Persistência local SQLite

**Data:** 2026-07-30 | **Dono:** Engenharia ASEP  
**Versão:** 1.0 | **Status:** aceito pela implementação da Sprint 7.5

## Visão Geral

Este ADR registra a decisão de adicionar SQLite como terceiro backend das
portas de Run e Timeline.

## O Problema

Memória não é durável; JSON reescreve documentos completos. Era necessária
persistência local transacional sem servidor e sem mudar consumidores.

## A Solução

Usar `sqlite3`, dois adapters e uma camada compartilhada de conexão/schema,
selecionados pela Factory e Configuration.

## Explicação simples

A ASEP ganhou um caderno organizado e durável, mas continua pedindo dados pela
mesma “gaveta” abstrata.

## Explicação técnica

Runs e eventos usam payload JSON dos codecs existentes. Chaves operacionais
ficam em colunas. Um banco contém `runs` e `timeline_events`; não há foreign key.

## Contexto

Sprints 7.1–7.4 estabeleceram backends file, Factory e Configuration. SQLite
entra como adapter, não como mudança no domínio ou nos serviços.

## Alternativas

1. Somente JSON: rejeitada pela reescrita integral.
2. SQLAlchemy/Alembic: rejeitada como complexidade prematura.
3. Banco servidor: rejeitado para o caso local desta fase.
4. Uma tabela genérica: rejeitada por perder identidade semântica/índice.
5. Duas tabelas com payload canônico: escolhida.

## Decisão

- usar apenas `sqlite3`;
- criar banco/schema automaticamente;
- validar conjunto exato de colunas;
- usar uma conexão transacional curta por operação;
- compartilhar um banco entre os dois repositories;
- reutilizar codecs;
- fazer upsert de Run e append-only de Timeline;
- manter consumidores dependentes apenas dos Protocols.

## Justificativa

A decisão maximiza reuso e compatibilidade, entrega durabilidade local e
preserva baixo custo operacional.

## Componentes envolvidos

Configuration, RepositoryFactory, SQLiteDatabase, adapters, codecs, erros e
portas.

## Fluxo completo

```text
settings -> Factory -> adapters -> SQLiteDatabase -> sqlite3 -> asep.db
services ------------> protocols
```

A linha inferior evidencia que serviços não atravessam a fronteira.

## Dependências

Somente biblioteca padrão como nova infraestrutura. Não há ORM nem servidor.

## Exemplos

`ASEP_STORAGE_BACKEND=sqlite` e
`ASEP_SQLITE_DATABASE=storage/asep.db`.

## Consequências

Positivas: durabilidade, transação, índice, substituibilidade e zero serviço
externo. Negativas: schema precisa evoluir; lock/concorrência requer política;
payloads não são expostos como colunas consultáveis.

## Benefícios

Consultas locais mais adequadas, atualização por linha, histórico reaberto por
novas instâncias e integração transparente com Query/Metrics/Dashboard.

## Testes

Testes de contrato para três backends e testes SQLite de schema, persistência,
falhas e integração.

## Erros comuns

Confundir SQLite com backend padrão; editar schema manualmente; deixar serviços
importarem adapters; assumir migrations inexistentes.

## Limitações

Sem migrations, pool, retry, WAL configurável, backup ou foreign key.

## Evolução futura

Qualquer migration/versionamento, tuning ou banco servidor requer novo ADR ou
supersessão explícita.

## Referências

[Sprint 7.5](../phase-07/Sprint-7.5-SQLite-Repository.md),
[schema](../persistence/DatabaseSchema.md) e
[arquitetura](../persistence/SQLiteArchitecture.md).

## Relacionado a

Sprint 7.5; Fase 07; componentes SQLite; testes de repositories;
[Roadmap](../architecture/Roadmap.md);
[Architecture v1](../architecture/ASEP-Architecture-v1.md);
[Glossário](../glossary/PersistenceGlossary.md).
