# Relatório de Testes — Sprint 2

**Data:** 2026-07-28  
**Ambiente:** Windows; Python 3.14.4, compatível com Python 3.12+  
**Resultado:** aprovado para encaminhamento ao QA independente

## Resultado

- 38 testes aprovados;
- 0 falhas;
- cobertura total: 91%;
- módulos novos: 81% a 100%;
- meta informativa provisória de 80% atendida pelos módulos novos;
- 37 YAML-fonte e 8 workflows registrados validados;
- compilação/imports válidos;
- dependências sem conflito.

## Cobertura por capacidade

| Capacidade | Evidência |
|---|---|
| UUID v4 e RunContext | validação positiva/negativa |
| State Manager | load, transição, histórico, atomicidade, sobrescrita |
| Workflow Engine | ordem, ciclo, próxima etapa, parallel/conditional |
| Agent Runtime | execução, agente ausente, resultado inválido |
| Business Analyst | Markdown e bloqueio por lacuna |
| Artifact Manager | metadata, checksum e traversal |
| Quality Gate | approved, approved with pending e blocked |
| Retomada | mesmo run_id, duas tentativas, sem repetir concluídas |
| E2E | CLI → Orchestrator → Engine → Runtime → Agent → Artifact → Gate → State |

## Demonstrações

1. execução aprovada no projeto real;
2. remoção de `scope.md` produz `blocked`;
3. restauração do scope e `resume` concluem com o mesmo run_id;
4. modos `parallel` e `conditional` são rejeitados.

## Limites

pytest-cov é provisório; não houve teste multiprocesso ou Security Review;
aprovação humana e cancelamento não foram implementados.
