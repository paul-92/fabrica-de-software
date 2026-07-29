# Runtime — output-validation

**Status:** especificação | **Versão:** 0.1.1 | **Dono:** Runtime Owner a nomear

## Objetivo

Garantir compatibilidade entre produtor e consumidor sem integrar modelos de IA nesta versão.

## Comportamento especificado

Validar required outputs, schema, nomes canônicos, links, classificação, evidências do gate e required inputs dos próximos agentes.

## Invariantes e falhas

Saída inválida retorna para correção com achados estruturados; ausência nunca é sucesso. Falhas emitem evento, preservam causa e não avançam o estado silenciosamente.

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
