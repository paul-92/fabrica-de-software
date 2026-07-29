# Error Handling

**ID:** ARCH-ERR-001 | **Versão:** 0.1.0 | **Status:** approved

## Taxonomia

| Categoria | Exemplo | Retry |
|---|---|---|
| validation | YAML/schema/input inválido | após correção |
| conflict | versão/estado/lock divergente | reabrir/revalidar |
| blocked | gate, aprovação ou dependência | após resolução |
| execution | adaptador/template falhou | conforme código |
| persistence | write/replace/audit falhou | recovery controlado |
| cancelled | cancelamento humano | não; nova execução |
| internal | erro não classificado | não automático |

Todo erro possui `code`, `category`, `safe_message`, `details` allowlisted,
`retryable`, `trace_id` e `next_action`. Causa técnica fica no log local sanitizado.

## Princípios

- falhar antes de mutar;
- não capturar e continuar silenciosamente;
- retry não é loop automático;
- nova tentativa recebe ID e preserva anterior;
- erro de auditoria ou persistência marca necessidade de recovery;
- CLI nunca mostra segredo ou traceback por padrão.

## Retomada

`resume` recarrega snapshot/audit, valida integridade, versões, required inputs,
gate/approval e lock; só então cria tentativa. Se reconciliação for ambígua, o
projeto fica `blocked` e solicita decisão humana.

## Testes

Fault injection em cada fronteira de escrita, tabela código→exit code, repetição
do comando, crash entre replace/audit e retomada após correção.
