# Runtime — artifact-generation

**Status:** especificação | **Versão:** 0.1.1 | **Dono:** Runtime Owner a nomear

## Objetivo

Padronizar criação e versionamento de artefatos sem integrar modelos de IA nesta versão.

## Comportamento especificado

Artefato recebe ID, tipo, versão, status, produtor, fontes, classificação, checksum, projeto e links de decisão.

## Invariantes e falhas

Escrita é atômica; substituição cria nova versão; artefato global exige sanitização e aprovação. Falhas emitem evento, preservam causa e não avançam o estado silenciosamente.

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
