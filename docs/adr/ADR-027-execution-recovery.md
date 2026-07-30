# ADR-027 — Supervisão e recuperação separadas do Agent Runtime

**Status:** aceito  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

O Agent Runtime já possui retry local opcional, mas coordenação de planos exige
uma fronteira capaz de classificar falhas, aplicar fallback e encerrar chamadas
com estado observável sem ampliar o contrato interno do Runtime.

## Decisão

Criar um `ExecutionSupervisor` que decora a porta `AgentRuntime` e delega
recuperação ao `ExecutionRecoveryService`. Uma máquina de estados explícita
valida o lifecycle. Classifier, retry, backoff, fallback, validação e métricas
são componentes separados e determinísticos.

Recovery permanece fora do Runtime porque retry técnico individual e política
de recuperação da execução possuem escopos diferentes. A composição deve
evitar habilitar ambos simultaneamente sem intenção explícita.

## Máquina de estados

Estados tornam transições, terminação e futuras compensações auditáveis.
`rolled_back` é reservado, mas não possui execução nesta Sprint.

## Preparação para rollback e compensação

`RecoveryResult.actions` e o estado `recovering` permitem registrar futuras
ações compensatórias. Implementar rollback distribuído exigirá persistência,
idempotência, correlação e um ADR próprio; nenhuma Saga foi antecipada.

## Alternativas consideradas

- ampliar AgentExecutionService: rejeitada por misturar execução e política;
- colocar recovery no Coordinator: rejeitada por acoplá-lo a falhas técnicas;
- lançar exceções sem resultado: rejeitada por dificultar consolidação;
- adotar Saga agora: rejeitada por ausência de transações distribuídas.

## Consequências

Coordinator continua dependendo de AgentRuntime e pode receber o Supervisor.
Workflow e Planning não conhecem Recovery. O custo é uma camada adicional de
composição e o risco de retry duplo se políticas forem configuradas em ambas as
camadas.

## Evidência

`src/asep/runtime/recovery/` e `tests/test_execution_recovery.py`.
