# Architecture Traceability Matrix

**ID:** ARCH-TRC-001 | **Versão:** 0.1.0 | **Status:** approved

| Requisitos | Componentes/artefatos | ADRs | Teste arquitetural |
|---|---|---|---|
| FR-001–003 | Project/Registry Loader, Input Validator | 003, 005 | init/load/referências inválidas |
| FR-004–007 | Contract/Workflow Loader, Engine | 004–006 | grafo e sequência |
| FR-008–010 | State Manager, Input Validator | 006 | tabela de estados/inputs |
| FR-011 | Artifact Manager | 011 | golden/manifest/atomic write |
| FR-012 | Gate Evaluator | 008 | gate com/sem evidência |
| FR-013 | Approval Manager | 009 | pause/approve/reject |
| FR-014–015 | Logging/Audit | 010 | correlação/replay/redaction |
| FR-016–018 | Error Handler, State Manager | 006–007 | fail/resume/cancel/crash |
| FR-019 | CLI | 002 | comandos/exit codes |
| FR-020 | AgentPort/BA Adapter | 013 | E2E sem rede/provider |
| NFR-001/006 | eventos, audit, typed errors | 007/010 | diagnóstico ponta a ponta |
| NFR-002 | atomic repository/state machine | 003/006 | fault injection |
| NFR-003 | security baseline, redaction | 003/010/011 | abuso/secret scan |
| NFR-004 | CLI/Rich isolado | 002 | tarefa do operador |
| NFR-005 | pacote local | 002/003 | matriz de ambiente pendente |
| NFR-007 | loaders/fingerprint | 004/005/006 | version mismatch |
| NFR-008 | technical risks | — | target pendente |

## Cobertura do MVP

Todos os requisitos Must possuem componente, decisão e abordagem de teste. FR-021
é suportado por `status`; FR-022 permanece Could e não altera o desenho do MVP.
