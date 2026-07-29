# ADR-008 — Modelo de Quality Gates

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
Gates precisam de critérios/evidência e owner registrado.
## Problema
Separar avaliação técnica de aprovação humana e evitar sucesso por ausência.
## Alternativas
Boolean manual; checklist Markdown livre; modelo estruturado com evidence refs.
## Decisão
GateDefinition declarativo; GateEvaluation imutável por tentativa; cada critério
recebe evidence refs/findings; decisão `approved|approved_with_pending|failed`.
## Justificativa
Torna ausência explícita e auditável.
## Consequências
Gate Evaluator não cria evidência nem assume autoridade. Exceção tem owner/validade.
## Riscos
Critérios vagos permanecem formalmente válidos. Schemas validam estrutura; Quality
revisa semântica nas fases aplicáveis.
