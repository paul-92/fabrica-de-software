# State Model

**ID:** ARCH-STA-001 | **Versão:** 0.1.0 | **Status:** approved

## Estados de Projeto

`created`, `ready`, `running`, `awaiting_approval`, `blocked`, `failed`,
`cancelled`, `completed`.

| Origem | Evento | Destino |
|---|---|---|
| created | project.validated | ready |
| ready | workflow.started | running |
| running | human_approval.requested | awaiting_approval |
| running | dependency.blocked | blocked |
| running | execution.failed | failed |
| running | project.cancelled | cancelled |
| running | workflow.completed | completed |
| awaiting_approval | approval.approved | running |
| awaiting_approval | approval.rejected | blocked |
| awaiting_approval | project.cancelled | cancelled |
| blocked | blockers.resolved | ready |
| blocked | project.cancelled | cancelled |
| failed | execution.resume_requested | ready |
| failed | project.cancelled | cancelled |

## Estados de Workflow/Etapa

`pending`, `ready`, `running`, `awaiting_approval`, `blocked`, `failed`,
`skipped`, `cancelled`, `completed`.

| Origem | Evento | Destino |
|---|---|---|
| pending | dependencies.completed | ready |
| pending | condition.not_applicable | skipped |
| ready | stage.started | running |
| running | approval.requested | awaiting_approval |
| running | blocker.detected | blocked |
| running | stage.failed | failed |
| running | stage.completed | completed |
| awaiting_approval | approval.approved | running ou completed |
| awaiting_approval | approval.rejected | blocked |
| blocked | blocker.resolved | ready |
| failed | retry.created | ready |
| pending/ready/running/awaiting_approval/blocked/failed | cancellation.confirmed | cancelled |

## Transições inválidas

Estado terminal (`completed`, `cancelled`, `skipped`) não reabre. `pending` não vai
direto a `running`; `failed` não vai direto a `completed`; aprovação não muda uma
etapa que não esteja aguardando. Toda rejeição informa estado atual, evento e
transições permitidas.

## Invariantes

- uma etapa `running` por workflow na versão 0.1;
- projeto `completed` implica etapas obrigatórias completas/skipped por condição;
- tentativa nova não apaga a anterior;
- cancelamento é terminal para a execução; retomada cria execução vinculada.
