# Workflow Engine Design

**ID:** ARCH-WFE-001 | **Versão:** 0.1.0 | **Status:** approved

## Responsabilidade

Interpretar uma definição validada e propor a próxima transição sequencial. O
Engine não executa agente, não grava estado e não aprova gate.

## Modelo 0.1

- estágios ordenados com dependências explícitas;
- modo aceito na execução: `sequential`;
- condição simples e determinística baseada em contexto já validado;
- retorno para correção via nova tentativa;
- `skipped` somente por condição declarada;
- uma etapa ativa por execução.

Definições que exigem `parallel` são rejeitadas ou precisam de perfil/tailoring
sequencial aprovado para o MVP. O workflow corporativo contém grupos paralelos
futuros; a execução 0.1 deve serializá-los por uma ordem registrada no plano,
sem fingir paralelismo.

## Interface

```text
plan(definition, context) -> ExecutionPlan
next(plan, state) -> TransitionProposal | NoOp
validate_transition(current, event) -> TransitionDecision
```

## Validações

IDs únicos, dependências existentes, grafo acíclico, pelo menos uma entrada,
agentes/gates registrados, condições conhecidas, estados terminais alcançáveis e
completion criteria definidos.

## Erros e testes

`WF_CYCLE`, `WF_UNKNOWN_STAGE`, `WF_UNSUPPORTED_MODE`, `WF_GATE_PENDING`,
`WF_DEPENDENCY_PENDING`, `WF_INVALID_TRANSITION`. Testes por tabelas cobrem ordem,
skip, correção, aprovação, bloqueio, falha, cancelamento e conclusão.
