# Runtime — input-validation

**Status:** especificação | **Versão:** 0.1.1 | **Dono:** Runtime Owner a nomear

## Objetivo

Impedir execução com entradas incompatíveis sem integrar modelos de IA nesta versão.

## Comportamento especificado

Validar schema, required inputs do contrato, produtor/origem, versão, integridade, autorização e consistência entre IDs.

## Invariantes e falhas

Lacuna crítica bloqueia; lacuna não crítica só vira hipótese com impacto, dono e gatilho explícitos. Falhas emitem evento, preservam causa e não avançam o estado silenciosamente.

## Entradas e saídas

Entradas carregam IDs, versões, classificação e autorização. Saídas incluem estado,
eventos, artefatos ou erro tipado, além de correlação com a tarefa.

## Critérios para implementação futura

- schema versionado e testes de contrato;
- idempotência, concorrência e recuperação verificadas;
- isolamento e modelo de autorização aprovados por Security;
- ADR aceito antes de escolher tecnologia.

## Referências

[`core/SYSTEM.md`](../core/SYSTEM.md),
[`runtime/agent-lifecycle.md`](agent-lifecycle.md) e
[`observability/status-model.md`](../observability/status-model.md).
