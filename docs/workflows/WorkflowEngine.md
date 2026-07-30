# Workflow Engine

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** Sprint 8.2

## Visão Geral

O Engine interpreta e valida `WorkflowDefinition`, executa Steps sequenciais e
retorna `WorkflowExecutionResult`. O Orchestrator limita-se ao lifecycle
externo de Run.

## O Problema

Na Sprint 8.1, coordenação e loop de Steps estavam na mesma classe.

## A Solução

Separar `WorkflowValidator`, `WorkflowStepExecutor`, `WorkflowExecutor` e
`WorkflowEngine`, mantendo aliases públicos compatíveis.

## Explicação simples

O Orchestrator abre e fecha o evento; o Engine lê o roteiro; o Validator confere
o roteiro; o Executor conduz; o StepExecutor chama cada tarefa.

## Explicação técnica

`WorkflowDefinition` contém id, nome, descrição, Steps, metadata e
`WorkflowExecutionPolicy`. Validator rejeita nulo, vazio, IDs inválidos ou
duplicados, Steps fora do Protocol e política ainda não suportada. Executor
compartilha Context, registra eventos de Step, controla status/cancelamento e
converte `WorkflowStepException` em `WorkflowFailure`.

## Componentes

Definition, Policy, ExecutionContext, ExecutionResult, Validator, StepExecutor,
Executor, Engine, Orchestrator, Timeline e repositories.

## Fluxo completo

```text
Orchestrator -> WorkflowEngine
                    |
                    v
             WorkflowValidator
                    |
                    v
             WorkflowExecutor
                    |
                    v
          WorkflowStepExecutor -> Step
                    |
                    v
            WorkflowExecutionResult
```

Engine registra `stage.*`, warning/error; Orchestrator registra `run.*` e Run.

## Dependências

Engine depende de componentes workflow. Executor depende de TimelineRecorder.
Nenhum conhece backend, Factory, Metrics, Dashboard, provider ou agente.

## Exemplos

```python
definition = WorkflowDefinition(
    id="demo",
    description="duas tarefas",
    steps=(FirstStep(), SecondStep()),
    metadata={"owner": "platform"},
)
result = engine.execute(definition, WorkflowExecutionContext(run_id="run"))
```

## Testes

`test_workflow_engine.py` cobre validações, policy, wrapping de exceção,
Context, resultado rico, Timeline, falha, cancelamento e delegação.

## Erros comuns

`stop_on_failure=False` é rejeitado, pois continuação ainda não existe.
Cancelamento é cooperativo. Falha de Step vira resultado FAILED; falha
estrutural gera `WorkflowValidationException`.

## Limitações

Sequencial/síncrono; sem paralelismo, condições, retry, timeout, subworkflow,
event bus ou agentes.

## Evolução futura

As classes formam pontos de extensão, mas capacidades futuras não estão
implementadas nem prometidas nesta Sprint.

## Referências

[Sprint 8.2](../phase-08/Sprint-8.2-Workflow-Engine.md),
[ADR-018](../adr/ADR-018-workflow-engine-separation.md) e
[Dependencies](Dependencies.md).

## Relacionado a

Fase 08; `asep.workflow`; testes Engine/Orchestrator; Roadmap; Architecture;
Glossário.
