# ADR-019 — Fronteira dos contratos de agentes

**Status:** aceito localmente  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

O Engine conhece somente `WorkflowStep`; runtime e providers possuem contratos
próprios. Integrar agentes concretos diretamente criaria dependência reversa e
duplicaria modelos de execução.

## Decisão

Definir `Agent` como Protocol síncrono com metadados e execução por
`AgentRequest`/`AgentContext`. Reutilizar `AgentContext`, `AgentResult` e status
existentes. Fazer a integração exclusivamente por `AgentStepAdapter`, que
satisfaz estruturalmente `WorkflowStep`.

## Consequências

- Engine permanece independente de agentes e providers;
- futuros agentes podem ser testados sem API externa;
- identidades são validadas na fronteira;
- resultado é compartilhado pelo contexto do workflow;
- o runtime legado permanece compatível e poderá ser adaptado separadamente.

## Alternativas rejeitadas

- fazer o Engine importar ou detectar agentes;
- transformar Provider em Agent;
- duplicar contexto, resultado ou status;
- migrar o runtime legado junto desta Sprint.

