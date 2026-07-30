# Auditoria arquitetural — RC1

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída em 2026-07-30

## Escopo e método

Inspeção dos 116 módulos Python, contratos, testes, ADRs e mapas. Um analisador
AST local contou componentes e procurou ciclos entre módulos `asep`.

## Resultado

Nenhum bloqueador crítico foi encontrado. Foram identificados **zero ciclos de
imports**. Engine, agents, providers, exporters e repositories mantêm as
fronteiras documentadas.

| Problema/evidência | Impacto | Recomendação | Ação no RC1 | Pendência |
|---|---|---|---|---|
| `Orchestrator` legado tem 565 linhas e `StageExecutionService`, 424 | manutenção média | continuar extrações apenas por caso de uso | nenhuma mudança funcional | revisar antes de ampliar esses fluxos |
| Protocol `Agent` formal e Protocol legado no runtime | ambiguidade média | planejar adapter/migração compatível | distinção documentada | não unificar sem Sprint própria |
| Dois `WorkflowDefinition`: loader YAML e Engine genérico | confusão nominal baixa | preservar namespaces e documentar | mantidos por compatibilidade | avaliar nomes em futura major version |
| Escrita atômica semelhante em três repositories file | dívida DRY média | extrair utilitário somente com testes comuns | não refatorado no hardening | candidato técnico futuro |
| Factory bundle cresce com cada repository | acoplamento de composição baixo | manter centralização enquanto pequeno | validado | reavaliar se novos domínios proliferarem |

## Dependências confirmadas

```text
CLI/API -> application -> ports
WorkflowOrchestrator -> WorkflowEngine
WorkflowOrchestrator -> WorkflowPersistencePort
WorkflowEngine -> WorkflowStep
Composition -> AgentRegistry -> AgentStepAdapter
RepositoryFactory -> memory/file/sqlite implementations
Metrics/Dashboard -> RunQueryService -> repository ports
```

O Engine não importa Agent Registry, Factory, SQLite ou Workflow Persistence.

## Decisão

RC1 arquiteturalmente aceitável, condicionado a versionar o worktree e repetir
os gates em clone limpo. Nenhum ADR novo foi necessário: o hardening não mudou
decisões arquiteturais.

