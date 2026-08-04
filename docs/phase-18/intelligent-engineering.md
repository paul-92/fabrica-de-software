# Fase 18 — Intelligent Engineering

**Dono:** Engenharia ASEP
**Versão:** 1.0
**Status:** concluída

## Objetivo

Representar planejamento assistido, geração explícita de plano, execução de
reparo e reflexão por contratos estruturados. A fase compõe capacidades
determinísticas; não implementa IA externa nem autonomia irrestrita.

## Fluxo implementado

```text
FailureAnalysis
  -> RepairProposalPlanner -> RepairProposal
  -> RepairPlanGenerator -> RepairPlan
  -> RepairExecutor -> RepairResult
  -> ReflectionEvaluator -> EngineeringReflection
```

## 18.1 — AI Planning Foundation

`RepairProposal` contém somente `summary`, `reasoning`, `candidate_files`,
`suggested_actions` e `confidence`. O modelo é estrito, imutável e não possui
código ou conteúdo de substituição. `RepairProposalPlanner` é a porta que
produz a proposta a partir de `FailureAnalysis`.

## 18.2 — Repair Plan Generation

`RepairPlanGenerator` transforma proposta em plano. A implementação inicial,
`DeterministicRepairPlanGenerator`, cria um `RepairChange` por arquivo
candidato e preserva as ações sugeridas como justificativa. Ela exige
`replacement_contents` explicitamente: não deduz, inventa ou gera código.
`test_paths` também é fornecido pelo chamador.

## 18.3 — Evaluation & Reflection

`EngineeringReflection` registra `summary`, outcome, lessons,
recommended_actions, `should_retry` e confidence. É descritiva, imutável e não
executável. `DeterministicReflectionEvaluator` distingue `SUCCEEDED`, `FAILED`
e `EXHAUSTED` e pode preservar mensagens do reparo como lições.

`should_retry` é somente uma recomendação. Ele não executa novamente o
RepairLoop, não cria uma execução e não aciona recovery.

## 18.4 — Autonomous Engineering Pipeline

`AutonomousEngineeringRequest` reúne `FailureAnalysis`, conteúdos explícitos e
caminhos de teste. `AutonomousEngineeringService` chama, uma única vez,
Planner, Generator, RepairExecutor e ReflectionEvaluator.
`AutonomousEngineeringResult` preserva `proposal`, `plan`, `repair_result` e
`reflection` para inspeção.

O nome “Autonomous” representa composição controlada da sequência. O serviço
não cria retry próprio, não interpreta a reflexão como comando e não inicia
outra tentativa quando `should_retry=True`.

## Fronteiras

- AI Planning não acessa filesystem nem subprocessos;
- não executa Tools ou DeveloperAgent;
- efeitos continuam atrás do `RepairExecutor` da Fase 17;
- `RepairProposal` nunca contém código;
- `replacement_contents` permanece entrada obrigatoriamente explícita;
- Reflection não altera arquivos ou estado;
- não há memória persistente, aprendizado ou IA externa;
- Planning, RepairLoop, ExecutionRecovery e IntelligentOrchestrator não foram
  alterados pela fase.

## Evidência

`tests/qa/ai_planning` cobre modelos, imutabilidade, Protocols, API pública,
geração de múltiplas mudanças, conteúdo ausente, reflexão dos três outcomes,
propagação entre componentes e ausência de nova tentativa automática.

## Limitações

A fase não produz conteúdo de código. Implementações futuras de
`RepairProposalPlanner` ou estratégias de conteúdo podem ser injetadas, mas
devem respeitar os contratos e políticas de execução existentes.

## Decisões

Nenhum ADR novo foi necessário. A fase aplica as decisões existentes de
separação entre planejamento, efeitos por Tools, Repair e retry operacional.

