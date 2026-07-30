# Recovery Policies

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** contrato ativo

## Retry

`RetryPolicy` limita tentativas entre 1 e 100, define intervalo, backoff,
categorias elegíveis e atraso máximo. `RetryDecision` pode ser `retry`,
`do_not_retry` ou `limit_exceeded`.

Backoffs disponíveis:

- constante: intervalo fixo;
- linear: intervalo multiplicado pela tentativa;
- exponencial: intervalo multiplicado por potência de dois.

O atraso é limitado por `max_delay_seconds`. Não há retry infinito.

## Classificação

Falhas são classificadas em validação, Tool, Agent, Workflow, infraestrutura,
timeout, configuração ou inesperada. A classificação usa tipos e resultados
estruturados; não consulta LLM.

## Fallback

As ações são:

- `fail`;
- `ignore_step`;
- `cancel_workflow`;
- `substitute_agent`;
- `alternative_step`.

Substituição e etapa alternativa exigem alvo explícito e diferente do atual.
Não há seleção inteligente. Rollback e compensação não são executados nesta
versão.

## Segurança operacional

O RecoveryService recebe uma operação por injeção e nunca chama Tool
diretamente. Exceções são convertidas em resultados estruturados sem armazenar
payload sensível na Timeline.
