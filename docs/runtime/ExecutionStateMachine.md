# Execution State Machine

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** contrato ativo

Estados:

```text
pending -> planning -> ready -> running
                                  |
                                  +-> retrying -> running
                                  +-> recovering -> running/succeeded/failed
                                  +-> succeeded
                                  +-> failed
                                  +-> cancelled

recovering -> rolled_back
```

Estados terminais não aceitam novas transições. Toda mudança passa por
`ExecutionStateMachine.transition`; transições ilegais geram
`InvalidStateTransitionError`. O histórico é preservado em memória na ordem
das transições.

`rolled_back` existe no contrato para preparar evolução, mas a Sprint 9.6 não
implementa rollback, Saga ou compensação automática.

Essa máquina supervisionada não substitui o `StateManager` persistente de Runs:
uma controla o lifecycle local de uma chamada recuperável; a outra continua
controlando execução e etapas do produto ASEP.
