# Prompt oficial da Sprint atual

**Sprint:** 9.1 — Intelligent Agent Runtime
**Estado:** implementada localmente; validação e publicação pendentes

## Objetivo

Implementar uma infraestrutura síncrona, determinística e observável para
executar os agentes formais da ASEP.

## Escopo entregue

- AgentRuntime, serviço, modelos, policy, validator e exceções;
- Registry, Timeline e métricas integrados por contratos;
- AgentStepAdapter integrado ao runtime sem acoplar o Engine;
- retry explícito, timeout observacional e idempotência local;
- segurança de metadados e compatibilidade com agente existente;
- documentação técnica e ADR-022.

## Evidência

- testes unitários e integrados em `tests/test_agent_runtime.py`;
- testes legados de contratos, Registry e Workflow preservados;
- gates finais: suíte, cobertura, `compileall`, links e `git diff --check`.

## Restrições

- nenhum agente autônomo, provider, fila, scheduler ou paralelismo;
- nenhuma memória vetorial, RAG ou planejamento multiagente;
- nenhum lock distribuído ou mudança de schema;
- nenhum commit, push ou tag automático.

## Limites

O timeout não interrompe chamada bloqueada; idempotência e métricas online são
locais à instância. A Sprint 9.2 não foi iniciada.

Referências:
[Sprint 9.1](../docs/phase-09/Sprint-9.1-Intelligent-Agent-Runtime.md),
[Agent Runtime](../docs/agents/AgentRuntime.md),
[ADR-022](../docs/adr/ADR-022-intelligent-agent-runtime.md) e
[NEXT_STEPS](../project/NEXT_STEPS.md).
