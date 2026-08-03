# ADR-030 — Fronteira do Intelligent Orchestrator

**Status:** aceito pela implementação da Fase 15 | **Versão:** 1.0

## Contexto

Business Engineering, Planning, Coordination, artefatos e Quality Gates já
possuíam contratos próprios, mas faltava um ponto de composição do fluxo.

## Decisão

`IntelligentOrchestratorService` coordena essas dependências e devolve um
resultado consolidado. Ele delega construção, planejamento, execução,
persistência e avaliação; não incorpora a lógica interna desses componentes.
Gate bloqueador prevalece sobre o status da coordenação. Falhas e resultados
parciais permanecem explícitos.

## Consequências

A fachada oferece rastreabilidade por run/project e mantém Dependency
Inversion. O custo é um ponto adicional de composição e a execução continua
síncrona. Evidência: `src/asep/orchestrator/intelligent.py`, modelos públicos e
`tests/qa/orchestrator/test_intelligent.py`.

