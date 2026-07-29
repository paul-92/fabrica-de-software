# Runtime — state

**Status:** especificação | **Versão:** 0.1.1 | **Dono:** Runtime Owner a nomear

## Objetivo

Definir o estado mínimo persistente sem integrar modelos de IA nesta versão.

## Comportamento especificado

Projeto, workflow run, stage run, task, agent run, approval, gate, artifact e event têm IDs estáveis, versão e relações causais.

## Invariantes e falhas

Atualizações usam controle de concorrência; histórico é append-only para auditoria; retenção segue classificação. Falhas emitem evento, preservam causa e não avançam o estado silenciosamente.

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
