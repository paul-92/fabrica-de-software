# Roadmap arquitetural

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** planejado

O roadmap registra intenção, não compromisso nem comportamento implementado.
Mudanças de contrato exigem decisão arquitetural e testes.

```mermaid
timeline
    title Evolução planejada da ASEP
    v0.6 : JSON concluído
         : Run Repository em memória concluído
         : Timeline em memória concluída
         : Run Query Service e CLI history concluídos
         : Metrics Service concluído
         : Dashboard API interna concluída
         : Claude Provider
    v0.7 : FileRunRepository concluído
         : FileTimelineRepository concluído
         : Repository Factory concluída
         : Configuration System concluído
         : SQLite Repository concluído
    v0.8 : Parallel Execution
         : Retry
         : Cancellation
         : Dashboard MVP
    v1.0 : Blueprint
         : API
         : Dashboard
         : Packaging
         : Documentation
         : Stable Public API
```

## v0.6

- exporter JSON — implementado;
- modelo e contrato Run Repository com implementação em memória — implementado;
- modelo, repository e recorder de Timeline em memória — implementados;
- consultas unificadas e interface CLI de histórico em memória — implementadas;
- integração da Timeline ao lifecycle e persistência durável — planejadas;
- Metrics Service somente leitura — implementado;
- Dashboard API interna e somente leitura — implementada;
- Claude Provider por `AgentProvider`.

## v0.8

- execução paralela real;
- política de retry;
- cancelamento coordenado;
- Dashboard MVP.

## v0.7

- 7.1 FileRunRepository — implementado;
- 7.2 FileTimelineRepository — implementado;
- 7.3 Repository Factory — implementada;
- 7.4 Configuration System — implementado;
- 7.5 SQLite Repository — implementado.

Entregas da fase de persistência v0.7:

- portas `RunRepository` e `TimelineRepository` preservadas;
- backends `memory`, `file` e `sqlite` substituíveis;
- criação centralizada pela `RepositoryFactory`;
- configuração imutável por defaults e variáveis `ASEP_*`;
- schema SQLite automático para Runs e Timeline;
- testes de contrato compartilhados entre os três backends;
- documentação de repositories, schema, arquitetura e configuração em
  [`docs/persistence`](../persistence/SQLiteRepositories.md).

A aplicação padrão continua usando repositories em memória. O sistema
`Configuration` centraliza defaults e overrides pelas variáveis `ASEP_*`,
produzindo um `ApplicationSettings` imutável consumido pela
`RepositoryFactory`. O backend `sqlite` compartilha um banco entre Runs e
Timeline, selecionável por `ASEP_STORAGE_BACKEND=sqlite` e
`ASEP_SQLITE_DATABASE`. YAML, TOML, JSON e configuração por CLI permanecem fora
do escopo.

## v1.0

- Blueprint;
- API;
- Dashboard;
- packaging;
- documentação;
- API pública estável.

## Pré-condições arquiteturais

- remover ou aceitar formalmente o acoplamento ExecutionGraph → provider model;
- superseder o ADR-013 para reconhecer providers externos;
- definir concorrência e locking antes de Run Repository/paralelismo;
- definir fluxo humano antes de retomar `awaiting_approval`;
- alinhar a versão mínima de Python;
- versionar contratos públicos antes da estabilidade v1.0.
