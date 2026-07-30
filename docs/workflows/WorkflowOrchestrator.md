# Workflow Orchestrator

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** Sprint 8.1

## Visão Geral

`WorkflowOrchestrator` inicia/finaliza a execução e delega interpretação e Steps
ao `WorkflowEngine`. Toda execução produz resultado, Run e Timeline.

## O Problema

Faltava um coordenador genérico para validar fluxo, falha, cancelamento e
observabilidade antes de integrar novos agentes.

## A Solução

Criar modelos pequenos e um serviço injetável sobre `RunRepository` e
`TimelineRepository`.

## Explicação simples

Workflow é um roteiro; o Orchestrator abre/fecha a execução e o Engine conduz
as tarefas.

## Explicação técnica

Desde a Sprint 8.2, validação e loop pertencem ao Engine. O Orchestrator mantém
PENDING/RUNNING, eventos `run.*`, persistência terminal e projeção de erro.

Estados:

```text
CREATED -> RUNNING -> COMPLETED
                   -> FAILED
                   -> CANCELLED
```

Eles são projetados em `RunStatus` como `PENDING`, `RUNNING`, `SUCCEEDED`,
`FAILED` e `CANCELLED`.

## Componentes

`Workflow`, `WorkflowStep`, `WorkflowContext`, `WorkflowStatus`,
`WorkflowFailure`, `WorkflowResult`, `WorkflowOrchestrator`, repositories,
`TimelineRecorder`, Query, Metrics e Dashboard.

## Fluxo completo

```text
Workflow + Context
       |
       v
persist PENDING -> persist RUNNING -> run.started -> WorkflowEngine
       |
       v
step.started -> Step.execute -> step.finished -> próxima Step
       |
       +--> exceção ------> error + FAILED
       `--> cancelamento -> warning + CANCELLED
       |
       v
persist terminal -> run.finished -> WorkflowResult
```

Metrics não recebe escrita: ele calcula sob demanda a partir do Run terminal.
Dashboard observa os mesmos repositories por `RunQueryService`.

## Dependências

O serviço conhece Engine, portas, modelos Run/Timeline e `TimelineRecorder`.
Não conhece backends, Factory, Metrics, Dashboard, providers ou agentes.

## Exemplos

```python
class AddStep:
    id = "add"

    def execute(self, context):
        context.values["total"] = 1

result = orchestrator.execute(
    Workflow(id="demo", steps=(AddStep(),)),
    WorkflowContext(run_id="run-1"),
)
```

Uma Step cancela cooperativamente com `context.request_cancellation()`.

## Testes

`tests/test_workflow_orchestrator.py` cobre execução simples/múltipla, ordem,
estados persistidos, falha, cancelamento, vazio, Timeline, Metrics, Dashboard,
três backends da Factory e snapshot do Context.

## Erros comuns

Workflow vazio ou IDs repetidos são inválidos. Exceção de Step não escapa:
torna-se `WorkflowFailure`. Cancelamento não interrompe thread; é observado
antes/depois de cada Step.

## Limitações

Somente execução síncrona/sequencial; sem agentes, retry, timeout, paralelismo,
resume, dependências entre Steps ou cancelamento preemptivo.

## Evolução futura

Capacidades futuras exigem Sprint/decisão própria e devem preservar as portas.

## Referências

[Sprint 8.1](../phase-08/Sprint-8.1-Workflow-Orchestrator.md),
[ADR-017](../adr/ADR-017-workflow-orchestrator-boundary.md) e
[Dependencies](Dependencies.md).

## Relacionado a

Fase 08; modelos em `asep.workflow`; teste do Orchestrator; Roadmap;
Architecture v1; Glossário.
