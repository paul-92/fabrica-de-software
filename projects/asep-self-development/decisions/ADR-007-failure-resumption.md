# ADR-007 — Tratamento de falhas e retomada

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
Falha não pode avançar silenciosamente; retry automático é perigoso.
## Problema
Preservar diagnóstico e permitir retomada segura.
## Alternativas
Retry automático; abortar sem retomada; erros tipados + retomada explícita.
## Decisão
Erros possuem categoria/código/retryable/next action. Retomada é comando humano,
revalida estado, versões, inputs, gates e dependências e cria nova tentativa.
## Justificativa
Mantém controle humano e histórico, compatível com efeitos locais.
## Consequências
Mais estados/cenários; tentativa anterior é imutável. Cancelamento é terminal.
## Riscos
Ambiguidade após crash. Bloquear quando reconciliação não for determinística.
