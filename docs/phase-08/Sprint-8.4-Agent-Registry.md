# Sprint 8.4 — Agent Registry

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída localmente

## Visão Geral

Fotografia do catálogo em memória para registrar e localizar agentes que
satisfazem os contratos da Sprint 8.3.

## O Problema

Os contratos formais existiam, mas a composição não possuía uma porta central,
isolada e determinística para localizar agentes disponíveis.

## A Solução

Foram criados o Protocol `AgentRegistry`, `InMemoryAgentRegistry` e uma
hierarquia mínima de exceções. O Registry não executa agentes nem conhece o
Workflow Engine.

## Explicação simples

O Registry é uma lista telefônica: cadastra especialistas e informa onde
encontrá-los, mas não realiza o trabalho deles.

## Explicação técnica

```text
Application Composition
          |
          v
 InMemoryAgentRegistry
     /    |    \
    v     v     v
 Agent A Agent B Agent C
          |
          v
   AgentStepAdapter
          |
          v
   WorkflowStep / Engine
```

## Operações e validações

- `register`: rejeita nulo, metadados inválidos, ausência de `execute` e ID
  duplicado;
- `unregister`: remove ou lança `AgentNotFoundException`;
- `get`/`contains`/`get_metadata`: consulta tipada por `AgentId`;
- `list_all`: retorna tupla ordenada lexicograficamente por `AgentId`;
- `find_by_capability`: compara o ID case-sensitive da capacidade e retorna
  todos os agentes em ordem determinística.

Uma tentativa duplicada não substitui o agente original. Após remoção, o mesmo
ID pode ser registrado novamente.

## Ciclo de vida

```text
startup -> criar Registry -> registrar agentes -> usar por injeção -> descartar
```

Cada instância possui estado próprio. Não há Singleton ou estado global.

## Testes

Os testes cobrem registro, validação, duplicidade, consulta, listagem,
capacidades, remoção, isolamento e integração com Steps comuns, Timeline e
métricas do workflow.

## Limitações

- somente memória;
- sem thread safety explícita, pois a composição atual é síncrona;
- sem persistência, plugins, discovery, ranking ou resolução singular;
- não protege segredos inseridos por uma implementação de agente em seu `repr`;
  metadados devem continuar livres de credenciais.

## Referências

[Agent Registry](../workflows/AgentRegistry.md),
[Agent Contracts](../workflows/AgentContracts.md) e
[ADR-020](../adr/ADR-020-in-memory-agent-registry.md).

