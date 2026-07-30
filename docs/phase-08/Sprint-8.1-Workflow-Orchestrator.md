# Sprint 8.1 — Workflow Orchestrator

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída

## Visão Geral

Fotografia da primeira Sprint da Fase 08: coordenação sequencial de Steps
simuláveis com persistência e observabilidade.

## O Problema

Era necessário validar controle de fluxo antes de agentes inteligentes.

## A Solução

Modelos canônicos e serviço síncrono injetável.

## Explicação simples

Um roteiro passa por tarefas na ordem e sempre termina com um resultado claro.

## Explicação técnica

Consulte [WorkflowOrchestrator](../workflows/WorkflowOrchestrator.md).

## Componentes

Workflow, Step, Context, Status, Failure, Result e Orchestrator.

## Fluxo completo

`created -> running -> completed|failed|cancelled`, com Run/Timeline.

## Dependências

Somente portas Run/Timeline; Metrics/Dashboard leem a projeção.

## Exemplos

Steps simuladas implementam `execute(context) -> None`.

## Testes

12 testes novos; suíte final da implementação: 612 aprovados.

## Limitações

Sem agentes reais, retry, paralelismo ou resume.

## Evolução futura

Não definida nesta fotografia; depende de Sprints posteriores.

## Referências

[ADR-017](../adr/ADR-017-workflow-orchestrator-boundary.md) e
[Fase 08](../history/Phase-08.md).

## Relacionado a

Sprint 8.1; Fase 08; `asep.workflow`; testes; Roadmap; Architecture; Glossário.
