# ADR-018 — Separação entre Orchestrator e Workflow Engine

**Data:** 2026-07-30 | **Dono:** Engenharia ASEP  
**Versão:** 1.0 | **Status:** aceito pela Sprint 8.2

## Visão Geral

O Orchestrator controla início/fim; Engine interpreta e executa.

## O Problema

Loop, validação, Timeline e lifecycle em uma classe dificultavam evolução.

## A Solução

Extrair Engine, Validator, Executor e StepExecutor.

## Explicação simples

Cada especialista ganhou uma função: conferir roteiro, conduzir e chamar tarefa.

## Explicação técnica

Aliases preservam `Workflow`, `WorkflowContext` e `WorkflowResult`; novos
contratos expõem Definition, ExecutionContext e ExecutionResult.

## Contexto

ADR-017 separou o coordenador genérico do Orchestrator de projetos.

## Alternativas

Manter classe única (rejeitada); framework externo (prematuro); componentes
pequenos explícitos (escolhido).

## Decisão

Orchestrator persiste Run e eventos run; Engine valida/delega; Executor controla
Steps/status e eventos stage; StepExecutor converte exceções.

## Justificativa

Baixo acoplamento, teste isolado, compatibilidade e pontos claros de extensão.

## Componentes

Todos os componentes de `asep.workflow`.

## Fluxo completo

`Orchestrator -> Engine -> Validator/Executor -> StepExecutor`.

## Dependências

Metrics continua read-only; nenhuma dependência em adapters ou agentes.

## Exemplos

Falha estrutural levanta exceção específica; falha de Step retorna FAILED.

## Consequências

Mais classes públicas, porém responsabilidades menores. Duas famílias de engine
continuam distintas: esta genérica e `SequentialWorkflowEngine` declarativo.

## Testes

Testes isolados mais regressão de compatibilidade 8.1.

## Limitações

Sem recursos futuros listados no roadmap.

## Evolução futura

Qualquer convergência de engines exige ADR supersessor.

## Referências

[Workflow Engine](../workflows/WorkflowEngine.md).

## Relacionado a

Sprint 8.2; Fase 08; ADR-017; testes; Architecture; Glossário.
