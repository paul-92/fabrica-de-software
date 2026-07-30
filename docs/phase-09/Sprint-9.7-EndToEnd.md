# Sprint 9.7 — End-to-End Execution Pipeline (RC2)

**Dono:** Engenharia ASEP | **Status:** implementada localmente  
**Data:** 2026-07-30

## Objetivo

Integrar os mecanismos existentes em uma execução real iniciada por objetivo,
sem criar novo mecanismo de domínio.

## Entregas

- ASEPEngine e função `asep.execute`;
- ExecutionPipeline, PipelineBuilder e PipelineValidator;
- GoalRequest, GoalResult e GoalExecutionContext;
- DeveloperAgent determinístico;
- plano real de quatro etapas;
- execução de ListDirectory, SearchFiles, ReadFile e ReadDocumentation;
- memória, Timeline, métricas, recovery e agregação;
- exemplos e testes E2E.

## Evidência funcional

```python
result = asep.execute(
    goal="Analise este projeto e explique sua arquitetura.",
    workspace=".",
)
```

O resultado contém quatro etapas, quatro artefatos e métricas de todas as
camadas. Falha recuperável é repetida pelo Supervisor; falha permanente produz
GoalResult failed.

## Limites

Composição local, síncrona, sequencial e em memória. Sem CLI nova, REST, Web,
LLM, scheduler ou paralelismo. Artefatos são retornados, não persistidos.

## Referências

[ASEP Engine](../runtime/ASEPEngine.md),
[Execution Pipeline](../runtime/ExecutionPipeline.md) e
[ADR-028](../adr/ADR-028-end-to-end-pipeline.md).
