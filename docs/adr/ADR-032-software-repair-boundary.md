# ADR-032 — Software Repair separado de Execution Recovery

**Status:** aceito pela implementação da Fase 17 | **Versão:** 1.0

## Contexto

Retry operacional repete uma operação que falhou. Reparar software exige
interpretar uma falha funcional, produzir mudanças diferentes e revalidar o
resultado. Misturar os dois ciclos tornaria policies de runtime responsáveis
por conteúdo de software.

## Decisão

Software Repair é um domínio separado. Seu loop recebe análise, Planner,
Executor e limite explícito. Todos os efeitos passam por `WriteFileTool` e
`RunTestsTool`. `ExecutionRecoveryService` não é alterado. Quality Gate
permanece consumidor separado do resultado consolidado.

## Consequências

O ciclo é finito, auditável e testável; falhas funcionais não são confundidas
com backoff ou fallback. A composição que desejar acionar Repair após um gate
bloqueado deverá fazê-lo explicitamente. A implementação atual é síncrona,
determinística e sem IA.

