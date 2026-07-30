# ADR-017 — Fronteira do Workflow Orchestrator

**Data:** 2026-07-30 | **Dono:** Engenharia ASEP  
**Versão:** 1.0 | **Status:** aceito pela Sprint 8.1

## Visão Geral

Registra um coordenador genérico separado do Orchestrator de projetos existente.

## O Problema

Reusar ou reescrever o Orchestrator legado misturaria workflow declarativo,
agentes, artefatos e quality gates com a infraestrutura simulada desta Sprint.

## A Solução

Adicionar `WorkflowOrchestrator` em `asep.workflow`, sem alterar o Orchestrator
existente.

## Explicação simples

Há dois maestros: um conduz a execução completa da ASEP; outro ensaia roteiros
genéricos com Steps.

## Explicação técnica

O novo serviço depende somente de Run/Timeline, captura exceções de Step,
suporta cancelamento cooperativo e retorna resultado estruturado.

## Contexto

Fases anteriores já possuem máquina de estados e Orchestrator de projetos. A
Sprint 8.1 pede infraestrutura genérica sem agentes reais.

## Alternativas

Alterar Orchestrator legado (rejeitada); executar callables sem modelos
(rejeitada); novo limite incremental (escolhido).

## Decisão

Preservar ambos os componentes; Metrics continua read-only; integração ocorre
pela persistência de Run e Timeline; cancelamento é cooperativo.

## Justificativa

Reduz risco, preserva APIs e torna Steps facilmente simuláveis.

## Componentes

`asep.workflow`, repositories, TimelineRecorder e projeções existentes.

## Fluxo completo

`Workflow -> WorkflowOrchestrator -> repositories -> Query/Metrics/API`.

## Dependências

Sem imports de adapters, Factory, Metrics, Dashboard ou agentes no serviço.

## Exemplos

Uma exceção vira `WorkflowFailure` e Run `FAILED`, não escapa ao chamador.

## Consequências

Dois coordenadores precisam de nomes/documentação claros. O novo fluxo não
oferece recursos do legado como resume, artifacts e quality gates.

## Testes

Cobertura de estados, Timeline, métricas e três backends.

## Limitações

Sem paralelismo, retry, timeout, DAG ou cancelamento preemptivo.

## Evolução futura

Uma eventual convergência exige ADR supersessor e compatibilidade explícita.

## Referências

[Workflow Orchestrator](../workflows/WorkflowOrchestrator.md).

## Relacionado a

Sprint 8.1; Fase 08; testes; Roadmap; Architecture; Glossário.
