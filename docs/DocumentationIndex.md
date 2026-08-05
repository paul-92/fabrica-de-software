# Índice da documentação ASEP

**Público:** todas as pessoas que trabalham com a ASEP  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Visão Geral

Ponto de entrada para a documentação. O código é a fonte da verdade;
documentos explicam estado atual, decisões e história.

## O Problema

Arquivos sem mapa dificultam descobrir por onde começar e qual documento é
canônico.

## A Solução

Organizar por objetivo e fornecer público, descrição e referências cruzadas.

## Explicação simples

Este índice é o catálogo de uma biblioteca.

## Explicação técnica

### Estrutura

```text
docs/
|-- README.md
|-- DocumentationIndex.md
|-- architecture/       estado atual e mapas
|-- persistence/        implementação de storage
|-- phase-07/           fotografia da Sprint
|-- history/            narrativa de evolução
|-- adr/                decisões novas
|-- glossary/           termos por domínio
|-- architecture/decisions/  ADRs legados preservados
`-- *.md                documentos históricos/de apoio
```

### Trilhas recomendadas

| Público/objetivo | Comece por | Continue em |
|---|---|---|
| Instalar ou migrar | [Bootstrap](../BOOTSTRAP.md) | [Checklist de migração](../project/MIGRATION_CHECKLIST.md) |
| Continuar o projeto | [Estado atual](../project/PROJECT_STATE.md) | [Próximos passos](../project/NEXT_STEPS.md) |
| Iniciante | [README](README.md) | [Glossário](glossary/PersistenceGlossary.md) |
| Entender a Sprint 7.5 | [fotografia](phase-07/Sprint-7.5-SQLite-Repository.md) | [repositórios](persistence/SQLiteRepositories.md) |
| Arquitetura rápida | [Architecture Map](architecture/ArchitectureMap.md) | [Architecture v1](architecture/ASEP-Architecture-v1.md) |
| Implementar/manter SQLite | [SQLite Architecture](persistence/SQLiteArchitecture.md) | [Schema](persistence/DatabaseSchema.md) |
| Operar/configurar | [SQLite Configuration](persistence/SQLiteConfiguration.md) | [Troubleshooting dos repositories](persistence/SQLiteRepositories.md#possíveis-erros) |
| Compreender decisões | [ADR-016](adr/ADR-016-sqlite-persistence.md) | [Dependencies](persistence/Dependencies.md) |
| Compreender evolução | [History](history/HistoryOfASEP.md) | [Phase 07](history/Phase-07.md) |
| Entender a Sprint 8.1 | [fotografia](phase-08/Sprint-8.1-Workflow-Orchestrator.md) | [Workflow Orchestrator](workflows/WorkflowOrchestrator.md) |
| Entender a Sprint 8.2 | [fotografia](phase-08/Sprint-8.2-Workflow-Engine.md) | [Workflow Engine](workflows/WorkflowEngine.md) |
| Entender a Sprint 8.3 | [fotografia](phase-08/Sprint-8.3-Agent-Contracts.md) | [Agent Contracts](workflows/AgentContracts.md) |
| Entender a Sprint 8.4 | [fotografia](phase-08/Sprint-8.4-Agent-Registry.md) | [Agent Registry](workflows/AgentRegistry.md) |
| Entender a Sprint 8.5 | [fotografia](phase-08/Sprint-8.5-Workflow-Persistence.md) | [Workflow Persistence](workflows/WorkflowPersistence.md) |
| Entender a Sprint 9.1 | [fotografia](phase-09/Sprint-9.1-Intelligent-Agent-Runtime.md) | [Agent Runtime](agents/AgentRuntime.md) |
| Entender a Sprint 9.2 | [fotografia](phase-09/Sprint-9.2-Tool-Registry.md) | [Tool Architecture](tools/ToolArchitecture.md) |
| Entender a Sprint 9.3 | [fotografia](phase-09/Sprint-9.3-Agent-Memory.md) | [Agent Memory](agents/AgentMemory.md) |
| Entender a Sprint 9.4 | [fotografia](phase-09/Sprint-9.4-Planning-Engine.md) | [Planning Engine](planning/PlanningEngine.md) |
| Entender a Sprint 9.5 | [fotografia](phase-09/Sprint-9.5-Multi-Agent-Coordination.md) | [Agent Coordinator](agents/AgentCoordinator.md) |
| Entender a Sprint 9.6 | [fotografia](phase-09/Sprint-9.6-Execution-Recovery.md) | [Execution Supervisor](runtime/ExecutionSupervisor.md) |
| Entender a Sprint 9.7 | [fotografia](phase-09/Sprint-9.7-EndToEnd.md) | [ASEP Engine](runtime/ASEPEngine.md) |
| Avaliar a Sprint 9.8/RC2 | [fotografia](phase-09/Sprint-9.8-Platform-Hardening-RC2.md) | [Release Candidate 2](releases/ReleaseCandidate2.md) |
| Usar o Project Analyzer | [Overview](project-analysis/Overview.md) | [ProjectAnalyzer](project-analysis/ProjectAnalyzer.md) |
| Avaliar o RC1 | [Release Candidate](releases/ReleaseCandidate_RC1.md) | [Auditoria arquitetural](audits/ArchitectureAudit.md) |
| Migrar para RC2 | [Migration Guide RC2](migration/MigrationGuide-RC2.md) | [Checklist](../project/MIGRATION_CHECKLIST.md) |

### Catálogo de arquitetura

- [ASEP-Architecture-v1](architecture/ASEP-Architecture-v1.md): referência
  executável geral; público técnico.
- [ArchitectureMap](architecture/ArchitectureMap.md): cinco níveis de visão;
  iniciantes e arquitetos.
- [Core Domain](architecture/Core-Domain.md): fronteiras centrais.
- [Execution](architecture/Execution.md): lifecycle de execução.
- [ExecutionPackage](architecture/ExecutionPackage.md): pacote de provider.
- [ExecutionGraph](architecture/ExecutionGraph.md): representação canônica.
- [Providers](architecture/Providers.md): adapters de agentes externos.
- [Exporters](architecture/Exporters.md): Mermaid/BPMN/JSON.
- [CLI](architecture/CLI.md): comandos e códigos de saída.
- [RunRepository](architecture/RunRepository.md): porta e backends de Run.
- [ExecutionTimeline](architecture/ExecutionTimeline.md): eventos/repositories.
- [RunQueryService](architecture/RunQueryService.md): consultas.
- [MetricsService](architecture/MetricsService.md): métricas.
- [DashboardAPI](architecture/DashboardAPI.md): API somente leitura.
- [Roadmap](architecture/Roadmap.md): entregas e próximos marcos.

### Catálogo da Sprint 7.5

- [Sprint 7.5](phase-07/Sprint-7.5-SQLite-Repository.md): fotografia e
  rastreabilidade.
- [SQLiteRepositories](persistence/SQLiteRepositories.md): tutorial completo.
- [DatabaseSchema](persistence/DatabaseSchema.md): schema real.
- [SQLiteArchitecture](persistence/SQLiteArchitecture.md): camadas e fluxos.
- [SQLiteConfiguration](persistence/SQLiteConfiguration.md): ambiente/defaults.
- [Dependencies](persistence/Dependencies.md): dependências permitidas.
- [ADR-016](adr/ADR-016-sqlite-persistence.md): decisão arquitetural.
- [Phase-07](history/Phase-07.md): evolução da fase.
- [HistoryOfASEP](history/HistoryOfASEP.md): narrativa da plataforma.
- [PersistenceGlossary](glossary/PersistenceGlossary.md): termos.

### Documentos preservados

O [glossário legado](glossary.md), governança, métricas e catálogo continuam
acessíveis. ADRs anteriores permanecem em
[`architecture/decisions`](architecture/decisions/ADR-001-core-domain-boundaries.md);
novos ADRs documentais usam `docs/adr/` até decisão de consolidação.

### Catálogo da Sprint 8.1

- [Sprint 8.1](phase-08/Sprint-8.1-Workflow-Orchestrator.md): fotografia;
- [Workflow Orchestrator](workflows/WorkflowOrchestrator.md): modelo e fluxo;
- [Dependencies](workflows/Dependencies.md): fronteiras;
- [Phase 08](history/Phase-08.md): história da fase;
- [ADR-017](adr/ADR-017-workflow-orchestrator-boundary.md): decisão.
- [Sprint 8.2](phase-08/Sprint-8.2-Workflow-Engine.md): fotografia;
- [Workflow Engine](workflows/WorkflowEngine.md): interpretação e execução;
- [ADR-018](adr/ADR-018-workflow-engine-separation.md): separação.
- [Sprint 8.3](phase-08/Sprint-8.3-Agent-Contracts.md): fotografia;
- [Agent Contracts](workflows/AgentContracts.md): API e integração;
- [ADR-019](adr/ADR-019-agent-contract-boundary.md): fronteira.
- [Sprint 8.4](phase-08/Sprint-8.4-Agent-Registry.md): fotografia;
- [Agent Registry](workflows/AgentRegistry.md): contrato e políticas;
- [ADR-020](adr/ADR-020-in-memory-agent-registry.md): decisão.
- [Sprint 8.5](phase-08/Sprint-8.5-Workflow-Persistence.md): fotografia;
- [Workflow Persistence](workflows/WorkflowPersistence.md): modelo e fluxo;
- [ADR-021](adr/ADR-021-workflow-snapshot-persistence.md): decisão.
- [Sprint 8.6](phase-08/Sprint-8.6-Architecture-Hardening-RC1.md): hardening;
- [Release Candidate RC1](releases/ReleaseCandidate_RC1.md): gate consolidado.

### Catálogo da Sprint 9.1

- [Sprint 9.1](phase-09/Sprint-9.1-Intelligent-Agent-Runtime.md): fotografia;
- [Agent Runtime](agents/AgentRuntime.md): contratos, lifecycle e operação;
- [ADR-022](adr/ADR-022-intelligent-agent-runtime.md): fronteira do runtime.
- [Sprint 9.2](phase-09/Sprint-9.2-Tool-Registry.md): fotografia;
- [Tool Architecture](tools/ToolArchitecture.md): contratos e segurança;
- [ReadFileTool](tools/ReadFileTool.md), [SearchFilesTool](tools/SearchFilesTool.md),
  [ListDirectoryTool](tools/ListDirectoryTool.md) e
  [ReadDocumentationTool](tools/ReadDocumentationTool.md) e
  [RunTestsTool](tools/RunTestsTool.md): Tools iniciais;
- [ADR-023](adr/ADR-023-tool-registry.md): mediação pelo Registry.
- [Sprint 9.3](phase-09/Sprint-9.3-Agent-Memory.md): fotografia;
- [Agent Memory](agents/AgentMemory.md): contratos, stores e retenção;
- [ContextBuilder](agents/ContextBuilder.md): composição do contexto;
- [ADR-024](adr/ADR-024-agent-memory.md): fronteira de memória.
- [Sprint 9.4](phase-09/Sprint-9.4-Planning-Engine.md): fotografia;
- [Planning Engine](planning/PlanningEngine.md): fluxo e integração;
- [ExecutionPlan](planning/ExecutionPlan.md): contrato canônico;
- [ADR-025](adr/ADR-025-planning-engine.md): decisão de planejamento.
- [Sprint 9.5](phase-09/Sprint-9.5-Multi-Agent-Coordination.md): fotografia;
- [Agent Coordinator](agents/AgentCoordinator.md): fluxo e contratos;
- [Coordination Policies](agents/CoordinationPolicies.md): regras de seleção;
- [ADR-026](adr/ADR-026-multi-agent-coordination.md): separação da coordenação.
- [Sprint 9.6](phase-09/Sprint-9.6-Execution-Recovery.md): fotografia;
- [Execution Supervisor](runtime/ExecutionSupervisor.md): composição;
- [Recovery Policies](runtime/RecoveryPolicies.md): retry e fallback;
- [Execution State Machine](runtime/ExecutionStateMachine.md): estados;
- [ADR-027](adr/ADR-027-execution-recovery.md): decisão de recuperação.
- [Sprint 9.7](phase-09/Sprint-9.7-EndToEnd.md): fotografia;
- [ASEP Engine](runtime/ASEPEngine.md): fachada pública;
- [Execution Pipeline](runtime/ExecutionPipeline.md): fluxo completo;
- [Getting Started](examples/GettingStarted.md): exemplo inicial;
- [ADR-028](adr/ADR-028-end-to-end-pipeline.md): decisão da fachada.
- [Sprint 9.8](phase-09/Sprint-9.8-Platform-Hardening-RC2.md): auditoria e gates;
- [Release Candidate 2](releases/ReleaseCandidate2.md): estado do candidato;
- [Migration Guide RC2](migration/MigrationGuide-RC2.md): atualização segura.

### ADR Index vigente

- [ADR-016](adr/ADR-016-sqlite-persistence.md): persistência SQLite;
- [ADR-017](adr/ADR-017-workflow-orchestrator-boundary.md): Orchestrator;
- [ADR-018](adr/ADR-018-workflow-engine-separation.md): Workflow Engine;
- [ADR-019](adr/ADR-019-agent-contract-boundary.md): contratos de agentes;
- [ADR-020](adr/ADR-020-in-memory-agent-registry.md): Agent Registry;
- [ADR-021](adr/ADR-021-workflow-snapshot-persistence.md): snapshots;
- [ADR-022](adr/ADR-022-intelligent-agent-runtime.md): Agent Runtime;
- [ADR-023](adr/ADR-023-tool-registry.md): Tool Registry;
- [ADR-024](adr/ADR-024-agent-memory.md): Agent Memory;
- [ADR-025](adr/ADR-025-planning-engine.md): Planning Engine;
- [ADR-026](adr/ADR-026-multi-agent-coordination.md): coordenação;
- [ADR-027](adr/ADR-027-execution-recovery.md): recovery;
- [ADR-028](adr/ADR-028-end-to-end-pipeline.md): pipeline E2E.
- [ADR-029](adr/ADR-029-project-analyzer.md): análise determinística de projetos.

ADRs legados 001 e 015 permanecem em `architecture/decisions`. A Sprint 9.8
não alterou decisão arquitetural e não criou ADR.

### Project Analysis — Sprint 10.1

- [Fase 10 — Business Engineering](phase-10/business-engineering.md);
- [Fase 11 — integração com Planning](phase-11/integration.md);
- [Fase 12 — integração com Coordination](phase-12/coordination.md);
- [Fase 13 — execução pelo Runtime](phase-13/runtime-execution.md);
- [Fase 14 — DeveloperAgent e Tools](phase-14/developer-tool-execution.md);
- [Fase 15 — Intelligent Orchestrator](phase-15/intelligent-orchestrator.md);
- [Fase 16 — Software Generation & Validation](phase-16/software-generation-validation.md);
- [Auditoria documental até a Fase 16](audits/Phase-01-16-Documentation-Audit.md);
- [ADR-030](adr/ADR-030-intelligent-orchestrator-boundary.md) e
  [ADR-031](adr/ADR-031-controlled-software-generation.md).
- [Fase 17 — Software Repair](phase-17/software-repair.md);
- [ADR-032 — Software Repair separado de Retry](adr/ADR-032-software-repair-boundary.md).
- [Fase 18 — Intelligent Engineering](phase-18/intelligent-engineering.md).
- [Fase 20 — Intelligent Integration](phase-20/intelligent-integration.md).

- [Overview](project-analysis/Overview.md): arquitetura e API;
- [ProjectAnalyzer](project-analysis/ProjectAnalyzer.md): fachada e modelos;
- [Scanner](project-analysis/Scanner.md): percurso e exclusões;
- [Framework Detection](project-analysis/FrameworkDetection.md): frameworks;
- [Architecture Detection](project-analysis/ArchitectureDetection.md): estilos;
- [Heuristics](project-analysis/Heuristics.md): regras e limitações;
- [ADR-029](adr/ADR-029-project-analyzer.md): decisão arquitetural.

### Auditorias RC1

- [Architecture Audit](audits/ArchitectureAudit.md);
- [Code Audit](audits/CodeAudit.md);
- [Test Audit](audits/TestAudit.md);
- [Dependency Audit](audits/DependencyAudit.md);
- [Security Audit](audits/SecurityAudit.md);
- [Git Audit](audits/GitAudit.md).

### Continuidade e prompts oficiais

- [Bootstrap](../BOOTSTRAP.md): instalação em máquina limpa;
- [Estado atual](../project/PROJECT_STATE.md): fotografia comprovada;
- [Próximos passos](../project/NEXT_STEPS.md): handoff operacional;
- [Checklist de migração](../project/MIGRATION_CHECKLIST.md): antes, durante e depois;
- [Inventário de ambiente](../project/ENVIRONMENT_INVENTORY.md): requisitos não sensíveis;
- [Padrão documental](../prompts/DocumentationStandard.md);
- [Prompt documental](../prompts/DocumentationPrompt.md);
- [Modelo de Sprint](../prompts/SprintPromptTemplate.md);
- [Prompt da Sprint atual](../prompts/CurrentSprintPrompt.md).

## Componentes envolvidos

Toda a documentação e os módulos que ela descreve.

## Fluxo completo

Pergunta -> trilha -> visão geral -> detalhe técnico -> ADR/história -> testes.

## Dependências

Links relativos; código/testes como evidência; `core/` prevalece em governança.

## Exemplos

Para diagnosticar schema: índice -> Sprint 7.5 -> DatabaseSchema -> testes
SQLite.

## Testes

Validação automática local verifica links, seções, placeholders e
`git diff --check`.

## Erros comuns

Usar roadmap como descrição do código; tratar ADR em review como decisão
aceita; ignorar status/versão.

## Limitações

Alguns documentos históricos anteriores não seguem o template atual; foram
preservados para não apagar contexto.

## Evolução futura

Adicionar trilhas somente junto de capacidades implementadas e atualizar este
índice em toda Sprint documental.

## Referências

[README](README.md), [Architecture v1](architecture/ASEP-Architecture-v1.md) e
[Roadmap](architecture/Roadmap.md).

## Relacionado a

Sprint 7.5; Fase 07; ADRs; componentes; testes; arquitetura; glossários.
