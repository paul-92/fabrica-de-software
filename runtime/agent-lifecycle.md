# Runtime — agent-lifecycle

**Status:** especificação | **Versão:** 0.1.1 | **Dono:** Runtime Owner a nomear

## Objetivo

Definir estados e transições de uma execução de agente sem integrar modelos de IA nesta versão.

## Comportamento especificado

`created → loading → validating → executing → reviewing → validating_output → handing_off → completed`; qualquer estado ativo pode ir a `blocked`, `failed` ou `cancelled`.

## Invariantes e falhas

Cada transição exige precondição, timestamp, ator, motivo e evento; retry cria `attempt` novo. Falhas emitem evento, preservam causa e não avançam o estado silenciosamente.

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
