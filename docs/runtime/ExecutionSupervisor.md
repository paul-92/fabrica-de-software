# Execution Supervisor

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

## Objetivo

Supervisionar chamadas ao Agent Runtime, aplicar recuperação determinística e
encerrar cada execução em estado consistente.

`DefaultExecutionSupervisor` implementa a mesma porta `AgentRuntime`. Por isso,
o AgentCoordinator pode receber o Supervisor sem conhecer recuperação:

```text
AgentCoordinator -> ExecutionSupervisor -> AgentRuntime
                           |
                           v
                    RecoveryService
```

O Supervisor inicia a máquina em `pending`, transita por `ready` e `running`,
delega a execução e publica o evento terminal. Ele não executa Tools, não
seleciona agentes e não cria planos.

## Composição

O Runtime envolvido deve preferencialmente usar retry desabilitado quando o
Supervisor possuir política própria, evitando retries aninhados. Essa escolha
fica na raiz de composição; nenhum contrato anterior foi alterado.

## Observabilidade

Timeline registra início, conclusão, falha ou cancelamento. Métricas registram
execuções, sucesso/falha, retries, fallback, recuperações e duração.

Veja [Recovery Policies](RecoveryPolicies.md),
[State Machine](ExecutionStateMachine.md) e
[ADR-027](../adr/ADR-027-execution-recovery.md).
