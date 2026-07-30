# Documentação de Apoio

Esta pasta preserva documentos úteis anteriores: glossário, métricas, catálogo de serviços e governança histórica. O Core canônico está em `../core/`; em conflito, prevalece `core/SYSTEM.md` e `core/GOVERNANCE.md`. Conteúdo histórico não deve ser duplicado: vincule-o quando ainda aplicável.

A arquitetura executável vigente está documentada em
[architecture/ASEP-Architecture-v1.md](architecture/ASEP-Architecture-v1.md).
A navegação completa, trilhas por público e rastreabilidade estão no
[DocumentationIndex](DocumentationIndex.md).
A revisão de consistência e a decisão supersessora proposta estão em
[architecture/Architectural-Consistency-Review.md](architecture/Architectural-Consistency-Review.md).

## Persistência

O backend SQLite da Sprint 7.5 está documentado como uma trilha de estudo:

1. [Repositórios SQLite](persistence/SQLiteRepositories.md) — conceitos,
   contratos, leitura, escrita e comparação entre backends;
2. [Schema do banco](persistence/DatabaseSchema.md) — tabelas, colunas,
   payloads, chaves e índice;
3. [Arquitetura SQLite](persistence/SQLiteArchitecture.md) — camadas,
   responsabilidades, Factory e fluxos;
4. [Configuração SQLite](persistence/SQLiteConfiguration.md) — variáveis de
   ambiente, defaults, exemplos e diagnóstico.

O roadmap canônico permanece em
[architecture/Roadmap.md](architecture/Roadmap.md).

História e decisões da Fase 07:

- [fotografia da Sprint 7.5](phase-07/Sprint-7.5-SQLite-Repository.md);
- [história da Fase 07](history/Phase-07.md);
- [história arquitetural da ASEP](history/HistoryOfASEP.md);
- [ADR-016 — persistência SQLite](adr/ADR-016-sqlite-persistence.md);
- [mapa da arquitetura](architecture/ArchitectureMap.md);
- [glossário de persistência](glossary/PersistenceGlossary.md).
