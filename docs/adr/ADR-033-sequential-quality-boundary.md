# ADR-033 — Fronteira de identidade e persistência da qualidade sequencial

**Status:** aceito pela implementação da Fase 23.4 | **Versão:** 1.0

## Contexto

O Orchestrator sequencial possui lifecycle e identidade próprios no
`ExecutionState`. O `Run` público pertence a outro agregado e
`ProjectExecution` representa AI runtime em projeto/sessão. Quality Gates
também precisam de consulta estruturada sem eliminar os YAMLs de auditoria nem
autorizar descoberta livre de projetos no filesystem.

## Decisão

`SequentialExecution` permanece distinto de `Run` e `ProjectExecution`; não se
infere relação por igualdade de identificadores. `ExecutionState` é sua fonte
da verdade e é projetado por uma porta read-only da Application.

Resultados de gates são registrados em um `QualityGateResultRepository`
estruturado e imutável, separado do artefato YAML de auditoria. O YAML é gravado
primeiro; não se promete atomicidade ou rollback entre os stores.

Projetos sequenciais são resolvidos somente por mapeamento explícito fornecido
pelo host, com validação de identidade e confinamento opcional a raízes
autorizadas. A composição operacional injeta o mesmo resolver, estado e
repository no grafo de execução e consulta; não usa globals, service locator ou
extração por `app.state`.

## Consequências

A API pode comprovar ownership antes de consultar resultados, ocultar órfãos e
evitar paths públicos. Métricas e APIs de `Run` não mudam semanticamente. O
custo é exigir composição opt-in e cadastro explícito, além de admitir uma
janela audit-first caso a gravação estruturada falhe após o YAML. Backfill de
YAML histórico, unificação de agregados e integração com Intelligent
Orchestration exigem decisões futuras próprias.

