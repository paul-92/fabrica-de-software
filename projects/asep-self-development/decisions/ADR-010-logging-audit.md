# ADR-010 — Logging e auditoria

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
Diagnóstico e rastreabilidade têm retenção/finalidades diferentes.
## Problema
Registrar execução sem vazar conteúdo nem confundir log com evidência.
## Alternativas
Texto único; YAML acumulado; logging estruturado + audit JSONL.
## Decisão
Separar logs diagnósticos de audit trail append-only; ambos estruturados, com
allowlist/redaction, IDs de correlação e schemas.
## Justificativa
JSONL suporta append/replay simples; separação permite políticas futuras.
## Consequências
Dois sinks e reconciliação com state. Retenção permanece configuração pendente.
## Riscos
Linha truncada/dados sensíveis. Detectar truncamento e testar redaction.
