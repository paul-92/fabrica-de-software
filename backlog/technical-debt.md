# Débito técnico rastreável

**Atualizado em:** 2026-07-28  
**Status:** aberto

| ID | Origem | Débito | Risco | Estado | Gatilho de encerramento |
|---|---|---|---|---|---|
| DT-001 | QA Sprint 1 / ADR-002 | estrutura física não separa integralmente domain/application/ports/adapters/interfaces | acoplamento crescente | aberto | plano aprovado, migração e testes |
| DT-002 | QA Sprint 1 / ADR-010 | log diagnóstico não é separado de audit trail imutável | falsa confiança de auditoria | aberto | sink, schema e retenção independentes |
| DT-003 | QA Sprint 1 | `required_context` genérico não possui resolução semântica automática | contexto insuficiente | parcialmente tratado | validator declarativo |
| DT-004 | QA Sprint 1 | análise estática não configurada | defeitos de tipo/import | aberto | ferramenta e gate aprovados |
| DT-005 | Sprint 2 | pytest-cov e meta de 80% são provisórios | política não governada | aberto | decisão humana |
| DT-006 | Sprint 2 / ADR-003 | não há lock single-writer entre processos | corrida em retomada | aberto | lock e teste multiprocesso |
| DT-007 | Sprint 2 | aprovação humana via CLI não implementada | `awaiting_approval` não retomável | aberto | comando e autoridade aprovados |
| DT-008 | Sprint 2 | tailoring executa somente Business Analysis | cobertura funcional limitada | aberto por desenho | novos agentes aprovados |
| DT-009 | Security | review especializado pendente | risco residual desconhecido | aberto | relatório e `QG-SECURITY` |

Nenhum item desta lista autoriza a Sprint 3.
