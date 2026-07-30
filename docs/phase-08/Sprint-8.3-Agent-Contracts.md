# Sprint 8.3 — Agent Contracts

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída localmente

## Visão Geral

Fotografia dos contratos formais que permitem usar agentes como Steps sem
acoplar o Workflow Engine a providers ou implementações concretas.

## O Problema

O projeto possuía contratos específicos do runtime sequencial e de providers,
mas não uma interface pública para agentes especializados interoperarem com o
Engine genérico.

## A Solução

Foram criados identidade, metadados, capacidades, request, erro, Protocol,
exceções e `AgentStepAdapter`. Os modelos existentes `AgentContext`,
`AgentResult` e `AgentResultStatus` foram reutilizados.

## Explicação simples

O maestro agora possui uma ficha padrão para qualquer futuro músico, sem
precisar conhecer o instrumento ou seu fabricante.

## Explicação técnica

```text
WorkflowEngine -> WorkflowStep Protocol <- AgentStepAdapter -> Agent Protocol
                                                        |-> AgentRequest
                                                        |-> AgentContext
                                                        `-> AgentResult
```

O Engine continua dependendo apenas de `WorkflowStep`. O adapter valida
identidades, executa o agente e publica o resultado em `WorkflowContext.values`.

## API pública

- `Agent`, `AgentId`, `AgentMetadata`, `AgentCapability`;
- `AgentRequest`, `AgentContext`, `AgentResult`, `AgentStatus`;
- `AgentError`;
- `AgentException`, `AgentValidationException`,
  `AgentExecutionException`;
- `AgentStepAdapter`.

## Testes

Os testes cobrem validação, imutabilidade/serialização, Protocol estrutural,
execução, falhas, divergência de identidade e integração com o Workflow Engine.

## Limitações

- execução síncrona;
- nenhum agente inteligente concreto novo;
- o runtime legado continua compatível e não foi migrado nesta Sprint;
- não há discovery, registry dinâmico, retry ou seleção por capacidade.

## Referências

[Agent Contracts](../workflows/AgentContracts.md) e
[ADR-019](../adr/ADR-019-agent-contract-boundary.md).

