# Fase 17 — Software Repair

**Dono:** Engenharia ASEP
**Versão:** 1.0
**Status:** concluída

## Objetivo

Interpretar falhas funcionais de pytest, produzir um plano explícito, aplicar
mudanças por Tools e repetir a validação dentro de um limite determinístico.
Software Repair não é retry operacional e não contém IA.

## 17.1 — Foundation

Os modelos imutáveis `FailureAnalysis`, `RepairChange`, `RepairPlan`,
`RepairAttempt`, `RepairResult` e `RepairStatus` representam diagnóstico,
plano, histórico e resultado. Os Protocols `FailureAnalyzer`, `RepairPlanner`
e `RepairExecutor` mantêm o domínio desacoplado. `PytestFailureAnalyzer` e
`DeterministicRepairPlanner` oferecem implementações determinísticas.

## 17.2 — Planning & Execution

`ControlledRepairExecutor` aplica cada `RepairChange` por `WriteFileTool`, via
`ToolExecutor`, e depois solicita `RunTestsTool` com `RepairPlan.test_paths`.
Ele não usa filesystem nem subprocesso diretamente. Stdout e stderr não vazios
são preservados em `RepairAttempt.validation_output`.

Falha de escrita, validação vermelha ou exceção do serviço de Tools produz
`RepairStatus.FAILED`; somente todas as escritas e pytest verde produzem
`SUCCEEDED`. `FailureAnalysis` permanece em `final_analysis`. IDs de execução
são únicos por chamada para não colidir com a idempotência do serviço de Tools.

## 17.3 — Repair Loop

`RepairLoopPolicy.max_attempts` é positivo e explícito.
`RepairLoopContext` contém a análise inicial e a política.
`RepairLoopService` chama Planner e Executor uma vez por tentativa, preserva
`RepairAttempt` em ordem, encerra imediatamente no sucesso e retorna
`EXHAUSTED` ao atingir o limite. Exceções operacionais inesperadas dos contratos
não são mascaradas.

```text
FailureAnalysis -> RepairPlanner -> RepairPlan -> RepairExecutor
        ^                                            |
        |                    FAILED                  |
        +--------------------------------------------+
                     até max_attempts
```

## 17.4 — End-to-End Repair Pipeline

Os testes E2E usam workspace temporário e pytest real:

```text
software com bug -> RunTestsTool -> PytestFailureAnalyzer
 -> RepairLoopService -> ControlledRepairExecutor
 -> WriteFileTool -> RunTestsTool -> RepairResult
```

O caminho feliz corrige o arquivo na primeira ou segunda tentativa e termina
em `SUCCEEDED`. Um plano que mantém o bug repete apenas até o limite e termina
em `EXHAUSTED`.

## Repair não é Retry

`ExecutionRecoveryService` continua tratando repetição da mesma operação,
backoff, fallback, timeout e falhas operacionais. Repair interpreta uma falha
funcional e produz um novo plano de mudança. Nenhuma lógica foi movida para
`runtime.recovery`.

## Tools, segurança e Quality Gates

Escrita e pytest reutilizam as Tools e a política de workspace das Fases 14 e
16. Repair não altera essa política. `QualityGateEngine` continua separado e
pode avaliar um resultado consolidado por uma composição externa; a Fase 17
não transfere reparo ao gate nem adiciona integração ao Intelligent
Orchestrator.

## Evidência

- `tests/qa/repair/test_executor.py`: execução, falhas, output e paths;
- `tests/qa/repair/test_loop.py`: limites, histórico e propagação;
- `tests/qa/repair/test_repair_end_to_end.py`: filesystem e pytest reais;
- regressões de Coordination e Intelligent Orchestrator preservadas.

## Limitações

O analyzer é textual e específico para pytest. O planner padrão apenas produz
mudanças determinísticas a partir dos paths identificados; não gera correções
inteligentes. O loop é síncrono, local e não executa rollback.

## Decisão relacionada

[ADR-032](../adr/ADR-032-software-repair-boundary.md).

