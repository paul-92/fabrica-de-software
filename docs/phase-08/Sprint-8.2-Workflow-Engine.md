# Sprint 8.2 — Workflow Engine

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída

## Visão Geral

Fotografia da separação entre lifecycle externo e interpretação/execução.

## O Problema

O Orchestrator da 8.1 ainda continha o loop.

## A Solução

Engine composto por Validator, Executor e StepExecutor.

## Explicação simples

O maestro passou a abertura/execução da partitura a componentes especializados.

## Explicação técnica

Veja [Workflow Engine](../workflows/WorkflowEngine.md).

## Componentes

Definition, Policy, Context, Result, exceções, Validator, Executor e Engine.

## Fluxo completo

`Orchestrator -> Engine -> Validator -> Executor -> StepExecutor -> Result`.

## Dependências

Portas e Timeline; Metrics/Dashboard permanecem projeções de leitura.

## Exemplos

Steps simuladas leem/escrevem `context.values`.

## Testes

13 novos; regressão ao término: 625 aprovados.

## Limitações

Somente fluxo sequencial suportado.

## Evolução futura

Não documentada como funcionalidade até implementação.

## Referências

[ADR-018](../adr/ADR-018-workflow-engine-separation.md).

## Relacionado a

Sprint 8.2; Fase 08; Engine; testes; Roadmap; Architecture; Glossário.
