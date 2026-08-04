# Roadmap arquitetural

**Dono:** Engenharia ASEP | **Versão:** 1.3 | **Status:** atualizado até a Fase 18

O roadmap registra intenção, não compromisso nem comportamento implementado.
Mudanças de contrato exigem decisão arquitetural e testes.

O estado operacional, inclusive diferenças entre trabalho local e remoto, está
em [PROJECT_STATE](../../project/PROJECT_STATE.md). A próxima Sprint só deve ser
iniciada após o handoff descrito em
[NEXT_STEPS](../../project/NEXT_STEPS.md); esta fotografia não atribui número
novo aos itens futuros.

```mermaid
timeline
    title Evolução planejada da ASEP
    v0.6 : JSON concluído
         : Run Repository em memória concluído
         : Timeline em memória concluída
         : Run Query Service e CLI history concluídos
         : Metrics Service concluído
         : Dashboard API interna concluída
         : AgentProvider e CodexProvider concluídos
    v0.7 : FileRunRepository concluído
         : FileTimelineRepository concluído
         : Repository Factory concluída
         : Configuration System concluído
         : SQLite Repository concluído
    v0.8 : Workflow Orchestrator sequencial concluído
         : Workflow Engine separado concluído
         : Agent Contracts concluídos
         : Agent Registry concluído
         : Workflow Persistence concluída
         : Architecture Hardening RC1 concluído localmente
    v0.9 : Intelligent Agent Runtime concluído localmente
         : Tool Contracts e Tool Registry concluídos localmente
         : Agent Memory e Context Management concluídos localmente
         : Planning Engine concluído localmente
         : Multi-Agent Coordination concluída localmente
         : Intelligent Execution & Recovery concluída localmente
         : End-to-End Execution Pipeline concluído localmente
         : Platform Hardening RC2 validado tecnicamente
    v1.0 : Blueprint
         : Project Analyzer determinístico concluído localmente
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
- provider Codex por `AgentProvider`; Claude não está implementado.

## v0.8

- 8.1 Workflow Orchestrator sequencial e simulável — implementado;
- 8.2 Workflow Engine separado — implementado;
- 8.3 Agent Contracts e adapter de Step — implementado;
- 8.4 Agent Registry em memória — implementado;
- 8.5 Workflow Persistence — implementado;
- 8.6 Architecture Hardening & RC1 — concluído localmente;

## v0.9

- 9.1 Intelligent Agent Runtime — implementado localmente;
- 9.2 Tool Contracts & Tool Registry — implementada localmente;
- 9.3 Agent Memory & Context Management — implementada localmente;
- 9.4 Planning Engine — implementada localmente.
- 9.5 Multi-Agent Coordination — implementada localmente.
- 9.6 Intelligent Execution & Recovery — implementada localmente.
- 9.7 End-to-End Execution Pipeline — implementada localmente; fachada pública
  Python disponível.
- 9.8 Platform Hardening & Release Candidate 2 — validada tecnicamente;
  publicação depende de gates operacionais.

O runtime é síncrono, resolve agentes pelo Registry e integra Timeline e
métricas. Paralelismo, agentes autônomos, memória semântica e infraestrutura
distribuída continuam fora do estado implementado.

Itens futuros sem Sprint aprovada:

- execução paralela real;
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

- 10.1 Project Analyzer determinístico — implementado localmente;
- Fase 10 Business Engineering — modelos, análise, parser e BlueprintBuilder
  implementados;
- Fase 11 Business Engineering → Planning — implementada;
- Fase 12 Planning → Agent Coordination — implementada;
- Fase 13 Coordination → Agent Runtime — implementada e coberta por E2E;
- Fase 14 DeveloperAgent → Tool Execution — implementada;
- Fase 15 Intelligent Orchestrator — concluída;
- Fase 16 Software Generation & Validation Pipeline — concluída.

Subdivisões comprovadas da Fase 16: 16.1 reutilização da infraestrutura; 16.2
Safe WriteFileTool; 16.3 DeveloperAgent + WriteFileTool; 16.4 múltiplos
arquivos; 16.5 alteração explícita; 16.6 propagação de resultados; 16.7
validação automática; 16.8 Quality Gate da geração; 16.9 E2E requisito →
software validado.

## Fase 17 — Software Repair

- 17.1 Foundation — concluída;
- 17.2 Planning & Execution — concluída;
- 17.3 Repair Loop — concluída;
- 17.4 End-to-End Repair Pipeline — concluída.

Repair permanece determinístico, limitado e separado de retry operacional.

## Fase 18 — Intelligent Engineering

- 18.1 AI Planning Foundation — concluída;
- 18.2 Repair Plan Generation — concluída;
- 18.3 Evaluation & Reflection — concluída;
- 18.4 Autonomous Engineering Pipeline — concluída.

A fase compõe contratos determinísticos. Conteúdo de substituição continua
explícito; não há IA externa, memória persistente ou retry automático.

## Pré-condições arquiteturais

- preservar o isolamento ExecutionGraph/exporters confirmado pelo ADR-015;
- definir concorrência e locking antes de Run Repository/paralelismo;
- definir fluxo humano antes de retomar `awaiting_approval`;
- preservar Python mínimo `>=3.12` em código, pacote e documentação;
- versionar contratos públicos antes da estabilidade v1.0.
