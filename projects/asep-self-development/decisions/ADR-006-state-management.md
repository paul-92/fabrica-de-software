# ADR-006 — Gerenciamento de estado

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
Retomada/cancelamento exigem estado durável sem banco.
## Problema
Impedir transições inválidas e snapshots parciais.
## Alternativas
Estado implícito em arquivos; event sourcing completo; snapshot YAML + eventos.
## Decisão
Máquinas de estado explícitas para Project/Workflow/Stage, snapshot YAML atômico,
eventos auditáveis e controle single-writer com lock local.
## Justificativa
Mais simples que event sourcing completo e mais seguro que inferir diretórios.
## Consequências
Toda mutação passa pelo State Manager; estado terminal não reabre; versão e
`last_event_id` são persistidos.
## Riscos
Crash entre snapshot/audit. Usar intent/outcome, marker e reconciliação testada.
