# Roadmap arquitetural

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** planejado

O roadmap registra intenção, não compromisso nem comportamento implementado.
Mudanças de contrato exigem decisão arquitetural e testes.

```mermaid
timeline
    title Evolução planejada da ASEP
    v0.6 : JSON
         : Run Repository
         : Timeline
         : Metrics
         : Claude Provider
    v0.8 : Parallel Execution
         : Retry
         : Cancellation
         : Dashboard MVP
    v1.0 : Blueprint
         : API
         : Dashboard
         : Packaging
         : Documentation
         : Stable Public API
```

## v0.6

- exporter JSON;
- Run Repository para localização e consulta;
- timeline derivada do histórico;
- métricas;
- Claude Provider por `AgentProvider`.

## v0.8

- execução paralela real;
- política de retry;
- cancelamento coordenado;
- Dashboard MVP.

## v1.0

- Blueprint;
- API;
- Dashboard;
- packaging;
- documentação;
- API pública estável.

## Pré-condições arquiteturais

- remover ou aceitar formalmente o acoplamento ExecutionGraph → provider model;
- superseder o ADR-013 para reconhecer providers externos;
- definir concorrência e locking antes de Run Repository/paralelismo;
- definir fluxo humano antes de retomar `awaiting_approval`;
- alinhar a versão mínima de Python;
- versionar contratos públicos antes da estabilidade v1.0.
