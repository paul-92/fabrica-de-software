# Fase 15 — Intelligent Orchestrator

## Objetivo

Unificar a execução legada e a execução inteligente da ASEP sob um único ponto de orquestração, preservando compatibilidade e evitando duplicação de responsabilidades.

---

## Contexto

Atualmente a ASEP possui dois fluxos de execução.

### Pipeline legado

```text
Orchestrator
        │
        ▼
StageExecutionService
        │
        ▼
Legacy AgentRuntime
        │
        ▼
AgentResult
        │
        ▼
ArtifactManager
        │
        ▼
QualityGateEngine
        │
        ▼
ExecutionOutcome
```

Esse fluxo já possui:

- carregamento de projeto;
- controle de estado;
- execução sequencial de etapas;
- persistência de artefatos;
- quality gates;
- retomada de execução;
- resultado final.

---

### Pipeline inteligente

```text
BusinessDescription
        │
        ▼
RequirementAnalyzer
        │
        ▼
BlueprintBuilder
        │
        ▼
ProjectBlueprint
        │
        ▼
PlanningEngineAdapter
        │
        ▼
PlanningEngine
        │
        ▼
PlanningResult
        │
        ▼
AgentCoordinatorAdapter
        │
        ▼
AgentCoordinator
        │
        ▼
AgentExecutionService
        │
        ▼
DeveloperAgent
        │
        ▼
ToolExecutionService
        │
        ▼
ArtifactDraft
```

Esse fluxo já possui:

- modelagem de negócio;
- planejamento determinístico;
- coordenação multiagente;
- runtime inteligente;
- execução de Tools;
- produção de `ArtifactDraft`.

Ainda faltam:

- persistência dos artefatos;
- quality gates;
- atualização do estado;
- resultado final unificado.

---

## Decisão arquitetural

O pipeline legado não será removido nesta fase.

O `Orchestrator` será evoluído para suportar dois modos de execução:

```text
Orchestrator
        │
        ├── legacy
        │
        └── intelligent
```

A seleção do modo será explícita e não será inferida silenciosamente.

---

## Princípios

A evolução do Orchestrator deverá seguir estes princípios:

1. Preservar compatibilidade com o pipeline legado.

2. Reutilizar o `ArtifactManager`.

3. Reutilizar o `QualityGateEngine`.

4. Reutilizar o `StateManager`.

5. Não duplicar regras de persistência.

6. Não duplicar regras de quality gate.

7. Manter Planning, Coordination e Runtime desacoplados.

8. Permitir evolução incremental do pipeline inteligente.

---

## Responsabilidades do Intelligent Orchestrator

O modo inteligente deverá:

- receber uma descrição de negócio;
- criar um `ProjectBlueprint`;
- gerar um `PlanningResult`;
- coordenar agentes;
- executar Tools;
- coletar `ArtifactDraft`;
- persistir artefatos;
- executar quality gates;
- atualizar o estado da execução;
- produzir um resultado final.

---

## Fluxo proposto

```text
BusinessDescription
        │
        ▼
Business Engineering
        │
        ▼
ProjectBlueprint
        │
        ▼
Planning
        │
        ▼
PlanningResult
        │
        ▼
Agent Coordination
        │
        ▼
CoordinationResult
        │
        ▼
Artifact Collection
        │
        ▼
ArtifactManager
        │
        ▼
ArtifactReference
        │
        ▼
QualityGateEngine
        │
        ▼
ExecutionOutcome
```

---

## Estratégia de implementação

### Sprint 15.1

- documentação da arquitetura;
- definição dos modos de execução;
- identificação das responsabilidades compartilhadas.

**Status:** Em andamento

### Sprint 15.2

- criar o contrato do pipeline inteligente;
- definir entrada e saída do modo inteligente;
- não executar lógica ainda.

### Sprint 15.3

- implementar coleta de `ArtifactDraft` a partir de `CoordinationResult`;
- persistir com `ArtifactManager`;
- retornar `ArtifactReference`.

### Sprint 15.4

- integrar Quality Gates;
- bloquear ou aprovar artefatos persistidos.

### Sprint 15.5

- integrar estado da execução;
- produzir `ExecutionOutcome`.

### Sprint 15.6

- teste end-to-end:
  - descrição de negócio;
  - planejamento;
  - coordenação;
  - runtime;
  - Tools;
  - artefatos;
  - quality gates;
  - resultado final.

---

## Fora do escopo desta fase

Não será implementado agora:

- remoção do pipeline legado;
- migração automática de workflows antigos;
- execução paralela;
- rollback automático;
- self-healing;
- interface gráfica;
- integração com Codex ou LLMs.

---

## Critério de conclusão da Fase 15

A fase estará concluída quando a ASEP conseguir executar este fluxo:

```text
BusinessDescription
        │
        ▼
Planning
        │
        ▼
Coordination
        │
        ▼
Agent Runtime
        │
        ▼
Tools
        │
        ▼
ArtifactManager
        │
        ▼
Quality Gates
        │
        ▼
ExecutionOutcome
```

sem quebrar o pipeline legado.