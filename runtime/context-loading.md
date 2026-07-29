# Runtime — context-loading

**Status:** especificação | **Versão:** 0.1.1 | **Dono:** Runtime Owner a nomear

## Objetivo

Carregar apenas contexto autorizado e necessário sem integrar modelos de IA nesta versão.

## Comportamento especificado

Resolver projeto, tarefa, versões, artefatos por ID, classificação, escopo e limite de tamanho; registrar origem e checksum.

## Invariantes e falhas

Conteúdo não autorizado, versão ambígua ou dado sensível fora de política bloqueia o carregamento. Falhas emitem evento, preservam causa e não avançam o estado silenciosamente.

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
