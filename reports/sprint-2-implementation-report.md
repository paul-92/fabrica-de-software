# Relatório de Implementação — Sprint 2

**Projeto:** ASEP Self-development  
**Data:** 2026-07-28  
**Status:** `READY_FOR_QA_WITH_PENDING`

## Resumo executivo

A ASEP evoluiu de preparação para execução local de um workflow estritamente
sequencial. Cada execução recebe UUID v4, snapshot YAML atômico, histórico de
transições, log JSONL correlacionado, diretório próprio de artefatos e resultado
determinístico de quality gate. O Business Analyst local gera Markdown sem LLM,
rede ou inferência de requisitos.

## Estado inicial

- Sprint 1 aprovada com pendências;
- CLI apenas preparava o fluxo;
- ausência de estado e retomada;
- workflow corporativo incompatível por conter paralelo e condicional;
- ADR-002, audit trail, contexto semântico e política de cobertura pendentes.

## Componentes implementados

- RunContext e modelos estritos;
- State Manager com histórico e replace atômico;
- Sequential Workflow Engine;
- Agent Runtime e protocolo genérico;
- Business Analyst determinístico;
- Artifact Manager com checksum, metadata, colisão e proteção de path;
- Quality Gate Engine determinístico;
- Orchestrator de execução e retomada;
- `asep run` e `asep resume`;
- workflow piloto sequencial e ADR-014.

## Persistência

```text
projects/<project>/
├── .asep/runs/<run_id>/state.yaml
├── artifacts/runs/<run_id>/
│   ├── business-analysis/execution-summary.md
│   ├── business-analysis/execution-summary.md.metadata.yaml
│   └── quality-gates/<stage>-result.yaml
└── logs/runs/<run_id>.jsonl
```

## Decisões e desvios

- ADR-014 cria tailoring explícito de uma etapa; o workflow corporativo foi
  preservado.
- `parallel` e `conditional` falham com `CAPABILITY_NOT_SUPPORTED`.
- `asep approve` não foi implementado; `awaiting_approval` permanece fail-closed.
- pytest-cov foi adotado provisoriamente, sem converter 80% em gate aprovado.
- ADR-002 permanece aberto; não houve refatoração ampla nesta Sprint.

## Demonstração real

Execução `5a6e662e-43dd-4026-a956-fb94f0e6087b`:

- workflow `asep-self-development-sequential`;
- etapa `business_analysis`;
- agente `business-analyst`;
- `QG-ANALYSIS = APPROVED`;
- estado final `completed`;
- resumo, metadados, gate, estado e log persistidos.

Entrada ausente, retomada e workflow não suportado foram demonstrados por testes
de integração reproduzíveis.

## Riscos e recomendação

Débitos estão em [technical-debt.md](../backlog/technical-debt.md) e pendências em
[sprint-2-open-issues.md](sprint-2-open-issues.md). Recomenda-se QA independente
antes de qualquer planejamento da Sprint 3.
