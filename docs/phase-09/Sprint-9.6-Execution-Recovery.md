# Sprint 9.6 — Intelligent Execution & Recovery (RC2)

**Dono:** Engenharia ASEP | **Status:** implementada localmente  
**Data:** 2026-07-30

## Objetivo

Introduzir supervisão, classificação de falhas, retry limitado, backoff,
fallback e terminação consistente sem LLM ou execução direta de Tools.

## Arquitetura

```text
Workflow -> Planning -> Coordinator
                           |
                           v
                 ExecutionSupervisor
                           |
                 RecoveryService
                    /            \
              StateMachine    AgentRuntime
```

## Entregas

- Supervisor compatível com AgentRuntime;
- máquina com dez estados e histórico;
- oito categorias de falha;
- retry limitado e decisões explícitas;
- backoff constante, linear e exponencial;
- cinco ações de fallback declarativas;
- contexto, resultado, validação e exceções;
- Timeline e métricas;
- integração comprovada com Planning, Coordinator, Runtime e Workflow.

## Eventos

`execution_started`, `execution_completed`, `execution_failed`,
`execution_cancelled`, `retry_started`, `retry_completed`, `retry_failed`,
`fallback_started`, `fallback_completed`, `fallback_failed` e
`recovery_completed`.

## Limites

Local, síncrono e sequencial. Sem rollback, Saga, compensação automática,
scheduler, paralelismo ou rede. Timeout real continua limitado pelo Runtime
envolvido.

## Evidência

Código em `src/asep/runtime/recovery/`; testes em
`tests/test_execution_recovery.py`; decisão em
[ADR-027](../adr/ADR-027-execution-recovery.md).
