# Contratos de agentes

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Visão Geral

Contrato público, síncrono e independente de fornecedor para futuros agentes.

## O Problema

Providers representam adaptadores externos; Workflow Steps representam unidades
de coordenação. Nenhum desses conceitos, isoladamente, descreve identidade,
capacidade, solicitação e retorno de um agente ASEP.

## A Solução

O Protocol `Agent` expõe `metadata` e
`execute(request, context) -> AgentResult`. Modelos frozen validam e
serializam identidade, capacidades, request, metadados e erros.

## Contratos

| Contrato | Responsabilidade |
|---|---|
| `AgentId` | identidade estável e não vazia |
| `AgentMetadata` | nome, descrição, versão, capacidades e atributos |
| `AgentCapability` | capacidade declarada |
| `AgentRequest` | objetivo, inputs e metadados de uma solicitação |
| `AgentContext` | identidade e contexto imutável da execução |
| `AgentResult` | status, artefatos, mensagens, erros e metadados |
| `AgentError` | falha estruturada e serializável |
| `Agent` | interface estrutural de execução |
| `AgentStepAdapter` | interoperabilidade com `WorkflowStep` |

`AgentContext`, `AgentResult` e `AgentStatus` são reutilizações de
`asep.execution.models`, evitando dois formatos concorrentes.

## Fluxo

1. composição seleciona um `Agent`;
2. cria `AgentRequest` e `AgentContext`;
3. configura `AgentStepAdapter`;
4. Engine chama o adapter como qualquer `WorkflowStep`;
5. adapter valida o `run_id`, executa e valida o resultado;
6. resultado fica em `WorkflowContext.values`, sob
   `agent_results.<step_id>` por padrão.

Falhas inesperadas tornam-se `AgentExecutionException`; divergências de
contrato tornam-se `AgentValidationException`. O `WorkflowStepExecutor` mantém
seu comportamento e as converte na falha estruturada do workflow.

## Dependências

`asep.agents` depende apenas dos modelos de execução e do Protocol de workflow.
Não depende de Provider, API, Repository, Metrics, Orchestrator ou serviço
externo. O Workflow Engine não importa `asep.agents`.

## Exemplo

```python
step = AgentStepAdapter(
    step_id="review",
    agent=reviewer,
    request=request,
    context=agent_context,
)
workflow = WorkflowDefinition(id="review-flow", steps=(step,))
```

## Limitações

Não há implementação inteligente, execução assíncrona, descoberta ou escolha
automática por capacidade nesta Sprint.

## Referências

[Sprint 8.3](../phase-08/Sprint-8.3-Agent-Contracts.md) e
[ADR-019](../adr/ADR-019-agent-contract-boundary.md).

