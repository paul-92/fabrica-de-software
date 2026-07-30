# Fase 07 — Persistência extensível

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída até 7.5

## Visão Geral

A Fase 07 transformou repositories em memória em uma família configurável de
backends duráveis.

## O Problema

Dados efêmeros, criação manual de adapters e valores fixos impediam histórico
durável e composição uniforme.

## A Solução

Evolução incremental: file repositories, Factory, Configuration e SQLite.

## Explicação simples

A plataforma primeiro construiu gavetas duráveis, depois um responsável por
escolhê-las, depois um painel de escolha e finalmente uma gaveta SQLite.

## Explicação técnica

### Sprints

- 7.1: `FileRunRepository`;
- 7.2: `FileTimelineRepository`;
- 7.3: `RepositoryFactory`;
- 7.4: `Configuration` e `ApplicationSettings`;
- 7.5: adapters e infraestrutura SQLite.

## Componentes envolvidos

Protocols, modelos, codecs, file/sqlite adapters, Factory, Configuration,
Query, Metrics e Dashboard.

## Fluxo completo

```text
7.1/7.2 contratos duráveis
          |
          v
7.3 criação central
          |
          v
7.4 configuração central
          |
          v
7.5 SQLite substituível
```

## Dependências

Consumidores permanecem sobre portas. A camada de composição conhece Factory;
Factory conhece adapters; adapters conhecem infraestrutura.

## Exemplos

O mesmo `RunQueryService` recebe memory em teste, file para JSON local ou
sqlite para banco durável, sem alterar sua implementação.

## Decisões arquiteturais

Incrementalidade, compatibilidade de contratos, codecs compartilhados,
configuração imutável, criação central e ausência de ORM na primeira versão.

## Desafios e aprendizados

Escrita atômica portátil no Windows, preservação de timezone, ordenação
equivalente entre backends, schema incompatível e isolamento de consumidores.
Testes de contrato foram a principal prova de substituibilidade.

## Testes

Contratos Run/Timeline, testes específicos file/sqlite, Factory, Configuration
e integrações Query/Metrics/Dashboard.

## Erros comuns

Instanciar adapters em serviços; confundir backend padrão com sqlite; supor
migrations ou concorrência não implementadas.

## Limitações

Sem migrations, backup, paginação, pool, IoC ou banco servidor.

## Evolução futura

A próxima fase deve partir de uso observado. Recursos ainda não existentes não
são compromissos desta fase.

## Referências

[Roadmap](../architecture/Roadmap.md),
[Sprint 7.5](../phase-07/Sprint-7.5-SQLite-Repository.md) e
[History of ASEP](HistoryOfASEP.md).

## Relacionado a

Sprints 7.1–7.5; ADR-016; módulos de persistência; testes de contrato;
Architecture v1; glossário.
