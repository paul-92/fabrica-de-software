# Fase 15 — Intelligent Orchestrator

**Dono:** Engenharia ASEP
**Versão:** 1.0
**Status:** concluída e comprovada por implementação e testes

## Objetivo

Consolidar, numa fachada de aplicação tipada, Business Engineering, Planning,
coordenação de agentes, persistência de artefatos e Quality Gates. A fase não
cria um novo runtime: reutiliza os contratos e serviços existentes.

## Fluxo implementado

```text
BusinessDescription
  -> BlueprintBuilder -> ProjectBlueprint
  -> PlanningEngineAdapter -> PlanningResult / ExecutionPlan
  -> AgentCoordinatorAdapter -> CoordinationResult
  -> CoordinationArtifactCollector -> ArtifactManager
  -> QualityGateEngine -> GateResult
  -> IntelligentExecutionResult
```

`IntelligentOrchestratorService.execute()` constrói o blueprint, cria o plano,
coordena a execução, persiste os `ArtifactDraft` de cada `AgentResult`, avalia
um gate por resultado de agente e devolve uma consolidação imutável. Ele não
executa Tools nem agentes diretamente; essa responsabilidade permanece atrás
do Coordinator e do Runtime.

## Contratos públicos

- `IntelligentExecutionRequest`: `run_id`, `project_id`, `project_name`,
  `gate_id`, `BusinessDescription`, raiz dos artefatos e metadata JSON-safe;
- `IntelligentExecutionResult`: preserva os identificadores e reúne
  `ProjectBlueprint`, `PlanningResult`, `CoordinationResult`,
  `ArtifactReference`, `GateResult`, erros e metadata;
- `IntelligentExecutionStatus`: `COMPLETED`, `FAILED`, `PARTIAL` ou `BLOCKED`;
- `CoordinationArtifactCollector`: converte os drafts produzidos pelos agentes
  em referências persistidas, mantendo `run_id`, `project_id`, `stage_id` e
  `agent_id`.

Os modelos de entrada e saída são Pydantic estritos e imutáveis. Os contratos
existentes `ArtifactDraft`, `ArtifactReference`, `GateResult` e
`GateDecision` são reutilizados, sem modelos paralelos.

## Consolidação de status

Qualquer `GateDecision.BLOCKED` prevalece e produz `BLOCKED`. Sem gate
bloqueador, `CoordinationStatus.COMPLETED`, `FAILED` e `PARTIAL` são mapeados
respectivamente para os estados homônimos do resultado inteligente.
`APPROVED_WITH_PENDING` não bloqueia a consolidação.

O `QualityGateEngine` atualmente verifica: resultado do agente concluído,
existência de artefato, presença dos metadados de correlação, ausência de erros
críticos e etapa em execução. Ele não interpreta diretamente `exit_code` de
pytest; a falha chega pelo `ToolResult` e pelo resultado do agente.

## Artefatos e qualidade

O collector ignora execuções sem `agent_result`, persiste todos os drafts pelo
`ArtifactManager` e entrega referências ao gate correspondente à mesma etapa.
O manager aplica caminho relativo seguro, colisão explícita, escrita atômica,
metadata YAML e checksum SHA-256. Quality Gate continua separado do agente e
do collector.

## Evidência automatizada

`tests/qa/orchestrator/test_intelligent.py` cobre contratos, persistência e
metadata de artefatos, composição integral, estados concluído/parcial/falho e
bloqueado, além dos caminhos de geração validada e testes reprovados.
`tests/qa/agents/coordination/test_end_to_end.py` comprova a execução que
alimenta a coordenação. A evidência corresponde aos commits `e132995`,
`f11b6cc` e `bd138b2`.

## Limites

O fluxo atual é síncrono e determinístico. A fase não prova geração autônoma
por IA, paralelismo, distribuição ou interpretação semântica dos artefatos.

## Decisão relacionada

[ADR-030](../adr/ADR-030-intelligent-orchestrator-boundary.md).
