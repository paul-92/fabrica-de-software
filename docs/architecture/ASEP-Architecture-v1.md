# ASEP — Arquitetura v1

**Público:** pessoas desenvolvedoras e mantenedoras  
**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** vigente em 2026-07-30

## Objetivo

A ASEP é uma aplicação local que carrega projetos e catálogos versionados,
valida workflows, coordena etapas sequenciais, executa agentes internos ou um
provider injetado, persiste estado e artefatos e projeta workflows em formatos
de intercâmbio.

## Visão e filosofia

A implementação é um monólito modular Python. Modelos Pydantic formam os
contratos entre módulos; loaders isolam YAML e filesystem; serviços de
aplicação coordenam casos de uso; adaptadores encapsulam processos externos e
formatos de saída. A evolução é incremental: contratos existentes são
reutilizados e capacidades não suportadas falham explicitamente.

Princípios observados:

- validação estrita nas fronteiras;
- dependências explícitas e injetáveis;
- coordenação separada da execução interna de uma etapa;
- artefatos, estado e pacotes escritos atomicamente;
- prompts e pacotes determinísticos e neutros de fornecedor;
- representação canônica antes da visualização;
- erros esperados tipados e apresentados sem traceback pela CLI;
- suporte executável atual limitado a workflows sequenciais.

## Componentes e fluxo real

```mermaid
flowchart LR
    CLI["CLI: run / resume"] --> BOOT["ExecutionBootstrap"]
    BOOT --> LOADERS["Project, Registry e Workflow Loaders"]
    BOOT --> ENGINE["SequentialWorkflowEngine"]
    BOOT --> STATE["StateManager"]
    BOOT --> ORCH["Orchestrator"]
    ORCH --> STAGE["StageExecutionService"]
    STAGE --> RUNTIME["AgentRuntime"]
    RUNTIME --> BA["BusinessAnalystAgent determinístico"]
    STAGE --> PROMPT["PromptBuilder"]
    PROMPT --> PACKAGE["ExecutionPackageBuilder"]
    PACKAGE --> PORT["AgentProvider"]
    PORT --> CODEX["CodexProvider"]
    CODEX --> PROCESS["ProcessRunner + CodexResultParser"]
    STAGE --> ARTIFACT["ArtifactManager"]
    STAGE --> GATE["QualityGateEngine"]
    ORCH --> STATE

    GRAPHCLI["CLI: graph"] --> LOADERS
    GRAPHCLI --> GB["ExecutionGraphBuilder"]
    GB --> GRAPH["ExecutionGraph"]
    GRAPH --> JSON["ExecutionGraphSerializer"]
    GRAPH --> MERMAID["MermaidExporter"]
    GRAPH --> BPMN["BpmnExporter"]
    ENV["Defaults + ASEP_* environment"] --> CONFIG["Configuration"]
    CONFIG --> SETTINGS["ApplicationSettings imutável"]
    APPLICATION["Application composition"] --> CONFIG
    SETTINGS --> REPOFACTORY["RepositoryFactory"]
    REPOFACTORY --> RUNREPO["RunRepository"]
    REPOFACTORY --> TIMELINEREPO["TimelineRepository"]
    RUNMODEL["Run"] --> RUNREPO
    RUNREPO --> MEMORY["InMemoryRunRepository"]
    RUNREPO --> FILERUN["FileRunRepository"]
    RUNREPO --> SQLITERUN["SQLiteRunRepository"]
    FILERUN --> RUNJSON["runs.json"]
    RUNMODEL -. run_id .-> TIMELINE["TimelineEvent"]
    RECORDER["TimelineRecorder"] --> TIMELINE
    TIMELINE --> TIMELINEREPO
    TIMELINEREPO --> MEMORYTIMELINE["InMemoryTimelineRepository"]
    TIMELINEREPO --> FILETIMELINE["FileTimelineRepository"]
    TIMELINEREPO --> SQLITETIMELINE["SQLiteTimelineRepository"]
    FILETIMELINE --> TIMELINEJSON["timeline-events.json"]
    SQLITERUN --> SQLITEDB["asep.db"]
    SQLITETIMELINE --> SQLITEDB
    RUNREPO --> QUERY["RunQueryService"]
    TIMELINE --> QUERY
    QUERY --> HISTORY["CLI: runs / run show / run timeline"]
    QUERY --> METRICS["MetricsService"]
    QUERY --> DASHAPI["Dashboard API"]
    METRICS --> DASHAPI
    GENERICWF["Workflow + Steps simuladas"] --> WFORCH["WorkflowOrchestrator"]
    WFORCH --> WFENGINE["WorkflowEngine"]
    WFENGINE --> WFVALIDATOR["WorkflowValidator"]
    WFENGINE --> WFEXECUTOR["WorkflowExecutor"]
    WFORCH --> RUNREPO
    WFORCH --> TIMELINEREPO
```

O caminho `PromptBuilder → ExecutionPackageBuilder → AgentProvider` ocorre
somente quando um provider é injetado no `Orchestrator` ou diretamente no
`StageExecutionService`. A construção padrão usada pela CLI `run` não injeta
provider e executa o `BusinessAnalystAgent`. O comando `graph` cria atualmente
uma projeção estática do workflow; ele não lê um run nem relatórios de etapas.

## Limites

| Módulo | Pode depender de | Não deve depender de |
|---|---|---|
| `models`, `execution.models` | Pydantic e biblioteca padrão | CLI e adaptadores externos |
| `execution.engine` | workflow e estado tipados | filesystem, provider e exporters |
| `application` | domínio, portas, loaders e adaptadores injetados | CLI |
| `orchestrator` | serviços de aplicação e máquina de estados | subprocess e serialização de exporters |
| `prompting` | seus modelos | provider, processo e filesystem |
| `execution_package` | prompting e seus modelos | providers concretos e workflow engine |
| `providers` | `ExecutionPackage`, contrato e infraestrutura de processo | workflow engine, orchestrator e quality gates |
| `execution_graph` | workflow/estado/resultados necessários à projeção | CLI e exporters |
| `exporters` | `ExecutionGraph`, erros e bibliotecas de formato | workflow engine, orchestrator, providers concretos |
| `configuration` | biblioteca padrão e seus modelos imutáveis | repositories concretos, serviços e API HTTP |
| `repositories` | portas e implementações concretas de persistência | serviços consumidores e API HTTP |
| `cli` | casos de uso, loaders, builder e exporters públicos | detalhes internos de subprocess/layout |

Regras confirmadas no código:

- providers não dependem do Workflow Engine;
- `ExecutionPackage` não depende de provider concreto;
- `PromptBuilder` não executa providers;
- `StageExecutionService` usa o protocolo `AgentProvider`, não `CodexProvider`;
- serviços de consulta, métricas e Dashboard API recebem somente os protocolos
  `RunRepository` e `TimelineRepository`;
- composition roots carregam um único `ApplicationSettings` validado por
  `Configuration`;
- `RepositoryFactory` é o único ponto de seleção e criação das implementações
  concretas de repositories e depende somente de `ApplicationSettings`;
- `WorkflowOrchestrator` genérico depende das portas Run/Timeline e permanece
  separado do `Orchestrator` de projetos, agentes, artefatos e quality gates;
- `WorkflowEngine` interpreta/valida e delega o loop ao `WorkflowExecutor`;
- integrações externas são adaptadores (`CodexProvider`, `ProcessRunner`,
  exporters e loaders);
- Mermaid e BPMN recebem somente `ExecutionGraph`.

## Configuração

`Configuration.load()` cria um snapshot `ApplicationSettings` imutável. Os
valores padrão são usados quando a variável correspondente não existe; não há
leitura de YAML, TOML, JSON ou argumentos de CLI.

| Variável | Default | Regra |
|---|---|---|
| `ASEP_STORAGE_BACKEND` | `memory` | `memory`, `file` ou `sqlite` |
| `ASEP_STORAGE_DIRECTORY` | `storage` | caminho não vazio |
| `ASEP_RUNS_FILENAME` | `runs.json` | nome simples, sem diretórios |
| `ASEP_TIMELINE_FILENAME` | `timeline-events.json` | nome simples, sem diretórios |
| `ASEP_SQLITE_DATABASE` | `storage/asep.db` | caminho não vazio do banco |

```mermaid
flowchart TD
    DEFAULTS["Defaults da aplicação"] --> CONFIG["Configuration"]
    ENV["Variáveis ASEP_* opcionais"] --> CONFIG
    CONFIG --> SETTINGS["ApplicationSettings (frozen)"]
    SETTINGS --> FACTORY["RepositoryFactory"]
    FACTORY --> PORTS["Repository interfaces"]
    PORTS --> MEMORY["Implementações memory"]
    PORTS --> FILE["Implementações file"]
    PORTS --> SQLITE["Implementações SQLite"]
```

## Persistência SQLite

O backend `sqlite` usa exclusivamente `sqlite3` da biblioteca padrão.
`SQLiteDatabase` cria o diretório, o banco, as tabelas e o índice na primeira
abertura, valida as colunas esperadas e fornece conexões transacionais curtas.
Não há ORM, pool ou migrations versionadas.

```sql
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE timeline_events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE INDEX idx_timeline_events_run
    ON timeline_events (run_id);
```

Os payloads reutilizam `RunCodec` e `TimelineEventCodec`; portanto todos os
campos, metadata e timestamps com timezone seguem os mesmos contratos dos
backends em memória e arquivo.

Exceção conhecida: `execution_graph.models` e `execution_graph.builder`
importam `AgentExecutionStatus` de `asep.providers.models`. Portanto, a regra
“ExecutionGraph nunca depende de Providers” ainda não é verdadeira na v1.

## Extensibilidade

- Novo provider: implemente `AgentProvider`, devolva `AgentExecutionResult`,
  isole transporte/processo e injete o objeto.
- Novo exporter: aceite `ExecutionGraph`, produza uma string pura e exponha
  apenas a API intencional em `asep.exporters`.
- Novo quality gate: preserve o contrato `GateResult`; hoje não existe um
  protocolo público de gates, portanto substituir o engine requer injeção de
  objeto compatível.
- Novo comando CLI: componha APIs públicas e preserve stdout utilizável por
  pipelines, stderr operacional e erros `AsepError`.

Detalhes estão em [Providers](Providers.md), [Exporters](Exporters.md) e
[CLI](CLI.md).

## Situação e roadmap

As limitações e próximos marcos estão em [Roadmap](Roadmap.md). Divergências
documentais encontradas:

1. o [ADR-013](../../projects/asep-self-development/decisions/ADR-013-ai-provider-extensibility.md)
   proibia provider de IA no MVP, mas `AgentProvider` e `CodexProvider` foram
   implementados posteriormente sem ADR supersessor encontrado;
2. a independência total de `ExecutionGraph` em relação a providers não existe;
3. `ExecutionPackageWriter` existe, mas o fluxo com provider passa o pacote em
   memória e não o persiste;
4. `awaiting_approval` existe na máquina de estados, porém `prepare_resume`
   aceita somente `failed` e `blocked`;
5. o `pyproject.toml` declara Python `>=3.12`, enquanto requisitos recentes
   mencionam compatibilidade com Python 3.11.

## Documentos

- [Índice geral](../DocumentationIndex.md)
- [Mapa da arquitetura](ArchitectureMap.md)
- [Fotografia da Sprint 7.5](../phase-07/Sprint-7.5-SQLite-Repository.md)
- [Core Domain](Core-Domain.md)
- [Execution](Execution.md)
- [Execution Package](ExecutionPackage.md)
- [Execution Graph](ExecutionGraph.md)
- [Providers](Providers.md)
- [Exporters](Exporters.md)
- [CLI](CLI.md)
- [Roadmap](Roadmap.md)
- [Run Repository](RunRepository.md)
- [Execution Timeline](ExecutionTimeline.md)
- [Run Query Service](RunQueryService.md)
- [Metrics Service](MetricsService.md)
- [Dashboard API](DashboardAPI.md)
- [Repositórios SQLite](../persistence/SQLiteRepositories.md)
- [Schema SQLite](../persistence/DatabaseSchema.md)
- [Arquitetura SQLite detalhada](../persistence/SQLiteArchitecture.md)
- [Configuração SQLite](../persistence/SQLiteConfiguration.md)
- [Dependências SQLite](../persistence/Dependencies.md)
- [ADR-016 — persistência SQLite](../adr/ADR-016-sqlite-persistence.md)
- [História da Fase 07](../history/Phase-07.md)
- [Glossário de persistência](../glossary/PersistenceGlossary.md)
- [Workflow Orchestrator](../workflows/WorkflowOrchestrator.md)
- [Sprint 8.1](../phase-08/Sprint-8.1-Workflow-Orchestrator.md)
- [ADR-017](../adr/ADR-017-workflow-orchestrator-boundary.md)
- [Workflow Engine](../workflows/WorkflowEngine.md)
- [Sprint 8.2](../phase-08/Sprint-8.2-Workflow-Engine.md)
- [ADR-018](../adr/ADR-018-workflow-engine-separation.md)
- [Agent Contracts](../workflows/AgentContracts.md)
- [Sprint 8.3](../phase-08/Sprint-8.3-Agent-Contracts.md)
- [ADR-019](../adr/ADR-019-agent-contract-boundary.md)
- [Agent Registry](../workflows/AgentRegistry.md)
- [Sprint 8.4](../phase-08/Sprint-8.4-Agent-Registry.md)
- [ADR-020](../adr/ADR-020-in-memory-agent-registry.md)
- [Workflow Persistence](../workflows/WorkflowPersistence.md)
- [Sprint 8.5](../phase-08/Sprint-8.5-Workflow-Persistence.md)
- [ADR-021](../adr/ADR-021-workflow-snapshot-persistence.md)
- [Revisão de consistência arquitetural](Architectural-Consistency-Review.md)
- [ADR-015 proposto](decisions/ADR-015-provider-boundaries-and-execution-graph-isolation.md)
- [Plano de refatoração proposto](Provider-Graph-Refactoring-Plan.md)
- [Fase 15 — Intelligent Orchestrator](../phase-15/intelligent-orchestrator.md)
- [Fase 16 — Software Generation & Validation](../phase-16/software-generation-validation.md)
- [ADR-030 — fronteira do Intelligent Orchestrator](../adr/ADR-030-intelligent-orchestrator-boundary.md)
- [ADR-031 — geração controlada por Tools](../adr/ADR-031-controlled-software-generation.md)
- [Auditoria documental até a Fase 16](../audits/Phase-01-16-Documentation-Audit.md)
