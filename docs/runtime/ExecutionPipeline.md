# Execution Pipeline

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

## Fluxo

```text
GoalRequest
  -> WorkflowOrchestrator / WorkflowEngine
  -> PlanningEngine
  -> ExecutionPlan
  -> AgentCoordinator
  -> ExecutionSupervisor
  -> AgentExecutionService
  -> DeveloperAgent
  -> ToolExecutionService / ToolRegistry / Tools
  -> MemoryService
  -> ResultAggregator
  -> GoalResult
```

Nenhuma camada é reimplementada. `ExecutionPipeline` coordena o caso de uso;
`PipelineBuilder` apenas constrói e conecta instâncias. `PipelineValidator`
verifica a disponibilidade dos componentes e a existência de Tools.

O plano padrão possui quatro etapas: listar diretórios, localizar arquivos
Python, ler o README e ler a documentação arquitetural. Todas são executadas
por um agente determinístico através de Tools reais e restritas ao workspace.

## Dados

Memory registra objetivo, plano, resultado e observação após sanitização.
Timeline compartilha o mesmo repository durante todo o fluxo. Métricas reúnem
Planning, Coordination, Recovery, Agent Runtime, Tools, Memory, Workflow e
duração total.

Artefatos produzidos pelo agente são devolvidos no `GoalResult`; esta composição
não os grava em disco.

## Falhas

Falha de validação ou capability inexistente encerra o Workflow. Falhas
elegíveis podem ser repetidas pelo Supervisor. Falhas permanentes retornam
`GoalStatus.failed`, preservando Timeline e métricas.
