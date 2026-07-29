# ADR-009 — Aprovações humanas

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
O MVP é local, sem autenticação, mas decisões materiais precisam ser registradas.
## Problema
Pausar e retomar sem fingir identidade forte.
## Alternativas
Arquivo editado manualmente; aprovação externa; comando CLI com papel declarado.
## Decisão
ApprovalRequest estruturada muda estado para `awaiting_approval`; CLI registra
approve/reject, approver, papel, motivo/condições e timestamp; audit preserva.
## Justificativa
É implementável localmente e transparente sobre a confiança.
## Consequências
Sem autenticação, autoridade é declarativa; uso restrito a piloto confiável.
## Riscos
Impersonação local. Exibir aviso e exigir nova arquitetura antes de multiusuário.
