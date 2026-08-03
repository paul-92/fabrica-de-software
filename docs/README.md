# Documentação de Apoio

Esta pasta preserva documentos úteis anteriores: glossário, métricas, catálogo de serviços e governança histórica. O Core canônico está em `../core/`; em conflito, prevalece `core/SYSTEM.md` e `core/GOVERNANCE.md`. Conteúdo histórico não deve ser duplicado: vincule-o quando ainda aplicável.

A arquitetura executável vigente está documentada em
[architecture/ASEP-Architecture-v1.md](architecture/ASEP-Architecture-v1.md).
A navegação completa, trilhas por público e rastreabilidade estão no
[DocumentationIndex](DocumentationIndex.md).

As capacidades implementadas após o RC2 estão consolidadas na
[auditoria documental até a Fase 16](audits/Phase-01-16-Documentation-Audit.md),
com aprofundamento no [Intelligent Orchestrator](phase-15/intelligent-orchestrator.md)
e em [Software Generation & Validation](phase-16/software-generation-validation.md).
A revisão de consistência e a decisão supersessora proposta estão em
[architecture/Architectural-Consistency-Review.md](architecture/Architectural-Consistency-Review.md).

## Instalação e continuidade

- [Bootstrap](../BOOTSTRAP.md): instalação e validação em uma máquina limpa;
- [Estado atual](../project/PROJECT_STATE.md): fotografia técnica e operacional;
- [Próximos passos](../project/NEXT_STEPS.md): continuidade da Sprint;
- [Checklist de migração](../project/MIGRATION_CHECKLIST.md);
- [Inventário de ambiente](../project/ENVIRONMENT_INVENTORY.md);
- [prompts oficiais](../prompts/README.md).

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

Coordenação de workflows:

- [Sprint 8.1](phase-08/Sprint-8.1-Workflow-Orchestrator.md);
- [Workflow Orchestrator](workflows/WorkflowOrchestrator.md);
- [Fase 08](history/Phase-08.md);
- [ADR-017](adr/ADR-017-workflow-orchestrator-boundary.md).
- [Sprint 8.2](phase-08/Sprint-8.2-Workflow-Engine.md);
- [Workflow Engine](workflows/WorkflowEngine.md);
- [ADR-018](adr/ADR-018-workflow-engine-separation.md).
- [Sprint 8.3](phase-08/Sprint-8.3-Agent-Contracts.md);
- [Agent Contracts](workflows/AgentContracts.md);
- [ADR-019](adr/ADR-019-agent-contract-boundary.md).
- [Sprint 8.4](phase-08/Sprint-8.4-Agent-Registry.md);
- [Agent Registry](workflows/AgentRegistry.md);
- [ADR-020](adr/ADR-020-in-memory-agent-registry.md).
- [Sprint 8.5](phase-08/Sprint-8.5-Workflow-Persistence.md);
- [Workflow Persistence](workflows/WorkflowPersistence.md);
- [ADR-021](adr/ADR-021-workflow-snapshot-persistence.md).

Agentes inteligentes:

- [Sprint 9.1](phase-09/Sprint-9.1-Intelligent-Agent-Runtime.md);
- [Agent Runtime](agents/AgentRuntime.md);
- [ADR-022](adr/ADR-022-intelligent-agent-runtime.md).
- [Sprint 9.2](phase-09/Sprint-9.2-Tool-Registry.md);
- [Tool Architecture](tools/ToolArchitecture.md);
- [ADR-023](adr/ADR-023-tool-registry.md).
- [Sprint 9.3](phase-09/Sprint-9.3-Agent-Memory.md);
- [Agent Memory](agents/AgentMemory.md);
- [ContextBuilder](agents/ContextBuilder.md);
- [ADR-024](adr/ADR-024-agent-memory.md).
- [Sprint 9.4](phase-09/Sprint-9.4-Planning-Engine.md);
- [Planning Engine](planning/PlanningEngine.md);
- [ADR-025](adr/ADR-025-planning-engine.md).
- [Sprint 9.5](phase-09/Sprint-9.5-Multi-Agent-Coordination.md);
- [Agent Coordinator](agents/AgentCoordinator.md);
- [ADR-026](adr/ADR-026-multi-agent-coordination.md).
- [Sprint 9.6](phase-09/Sprint-9.6-Execution-Recovery.md);
- [Execution Supervisor](runtime/ExecutionSupervisor.md);
- [ADR-027](adr/ADR-027-execution-recovery.md).
- [Sprint 9.7](phase-09/Sprint-9.7-EndToEnd.md);
- [ASEP Engine](runtime/ASEPEngine.md);
- [ADR-028](adr/ADR-028-end-to-end-pipeline.md).

## Release Candidate

- [Sprint 8.6](phase-08/Sprint-8.6-Architecture-Hardening-RC1.md);
- [RC1](releases/ReleaseCandidate_RC1.md);
- [auditorias](audits/ArchitectureAudit.md);
- [guia de migração](migration/MigrationGuide.md).
- [Sprint 9.8](phase-09/Sprint-9.8-Platform-Hardening-RC2.md);
- [RC2](releases/ReleaseCandidate2.md);
- [guia de migração RC2](migration/MigrationGuide-RC2.md);
- [diagrama oficial](architecture/ArchitectureMap.md#diagrama-oficial-do-rc2).
