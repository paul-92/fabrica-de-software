# Arquitetura de Tools

**Público:** engenharia e segurança da ASEP  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

## Visão Geral

Tools são capacidades reutilizáveis e independentes de agentes. Toda execução
passa por contratos, Registry, validação, política e observabilidade.

```text
Workflow -> Agent Runtime -> ToolExecutor
                              |
                              v
                    ToolExecutionService
                      /       |       \
                Registry  Timeline  Metrics
                    |
                   Tool
```

## Contratos

- `Tool`, `ToolId`, `ToolMetadata` e `ToolCapability`;
- `ToolRequest`, `ToolContext`, `ToolResult` e `ToolError`;
- `ToolExecutionPolicy`, `ToolValidator` e `ToolExecutor`;
- `ToolRegistry` e `InMemoryToolRegistry`.

Modelos são imutáveis, estritos e restringem payloads a valores JSON.
Dependências concretas são injetadas.

## Ciclo de vida

```text
requested -> validated -> started -> succeeded
     |                       |       failed
     |                       `------ timed_out
     `------------------------------ rejected
```

Timeline recebe somente identificadores, capability, correlação, tentativa,
status e tipo do erro. Payload e output não são registrados.

## Segurança

A política comum de workspace resolve paths e exige contenção após resolução.
Ela rejeita:

- paths absolutos e traversal;
- symlinks cujo destino esteja fora do workspace;
- `.git`, `.ssh`, `.env`, `.netrc` e arquivos de credenciais;
- paths inexistentes ou workspace inválido.

Metadados derivados removem recursivamente `password`, `secret`, `token`,
`api_key` e `authorization`. Tools não recebem variáveis de ambiente
automaticamente.

## Retry, timeout e métricas

O padrão é uma tentativa, sem retry. Apenas falhas explicitamente recuperáveis
podem ser repetidas. Timeout do serviço é observacional; `RunTestsTool` também
propaga o timeout real do runner de processo.

`ToolMetricsRecorder` recebe totais, sucesso, falha, rejeição, timeout, retry,
duração, Tool e capability. A implementação inicial é local e em memória.

## Integração com agentes

`AgentExecutionService` aceita opcionalmente a porta `ToolExecutor` e delega
por `execute_tool`. Ele não importa `InMemoryToolRegistry`, Tools concretas ou
detalhes de filesystem/processo. Agentes não devem acessar recursos por fora
dessa fronteira.

## Limitações

- API síncrona e execução sequencial;
- Registry, métricas e idempotência apenas em memória;
- sem permissão por agente/capability nesta Sprint;
- busca limitada a 1.000 resultados;
- nenhum suporte a escrita foi criado;
- timeout genérico não interrompe código Python bloqueado.

## Referências

[Sprint 9.2](../phase-09/Sprint-9.2-Tool-Registry.md) e
[ADR-023](../adr/ADR-023-tool-registry.md).

