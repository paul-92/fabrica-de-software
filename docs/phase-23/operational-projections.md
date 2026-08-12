# Fase 23 — Projeções operacionais públicas

**Público:** produto, engenharia, arquitetura, qualidade e operações

**Dono:** Engenharia ASEP

**Versão:** 1.0

**Status:** em andamento; Sprints 23.1–23.4 concluídas

## Objetivo e fronteira

A Fase 23 evolui fatos operacionais internos para projeções públicas mínimas,
somente leitura e versionadas, preservando:

```text
Presentation → HTTP/API → Application → contratos operacionais existentes
```

Adapters HTTP não consultam registries, engines, repositories ou filesystem
diretamente. Composições operacionais são explícitas e mantêm uma única
instância de cada dependência compartilhada.

## Entregas concluídas

- **23.1:** projeção pública do runtime de agentes em
  `GET /api/v1/agents/runtime`;
- **23.2:** composição tipada que compartilha `AgentRegistry` e métricas entre
  `ASEPEngine` e a projeção HTTP;
- **23.3:** métricas detalhadas por agente e extensão compatível da projeção
  pública, sem inferir health, readiness ou availability;
- **23.4:** persistência estruturada de Quality Gates, projeção de
  `SequentialExecution`, resolução autorizada de projetos sequenciais, API
  pública opt-in e explorador detalhado em `/quality`.

A fase inteira não está encerrada: incrementos 23.5 ou posteriores dependem de
priorização explícita.

## Identidades operacionais

Três conceitos permanecem distintos:

- `Run` é o agregado público do `WorkflowOrchestrator` e alimenta métricas e
  dashboard;
- `SequentialExecution` é uma projeção read-only do `ExecutionState` do
  Orchestrator sequencial; seu `execution_id` é o `run_id` desse estado;
- `ProjectExecution` registra uma execução de AI runtime dentro de projeto e
  sessão da Application/API.

Igualdade acidental entre strings ou UUIDs não cria relação entre esses
agregados. A Fase 23.4 não alterou `Run`, `RunStatus`, métricas ou APIs de runs e
projetos.

## Quality Gate: fluxo e persistência

O fluxo implementado é:

```text
execução sequencial → QualityGateEngine → GateResult
→ artefato YAML de auditoria → StoredQualityGateResult
→ QualityGateResultRepository → Application query → HTTP → /quality
```

`StoredQualityGateResult` é imutável e preserva somente fatos estruturados. Os
backends memory, file e SQLite compartilham identidade
`(run_id, stage_id, gate_id)`, rejeitam duplicatas e ordenam deterministicamente
por stage, gate e instante de avaliação. File e SQLite sobrevivem à
reconstrução e falham explicitamente diante de conteúdo malformado.

O YAML existente continua sendo artefato de auditoria separado. A política é
audit-first: o YAML é persistido antes do registro estruturado. Não existe
transação atômica entre os dois stores e não há promessa de rollback conjunto.
Migração ou backfill de YAMLs históricos foi deliberadamente adiada.

## Consulta pública e segurança

O endpoint opt-in é:

```text
GET /api/v1/sequential-projects/{project_id}/executions/{execution_id}/quality-gates
```

Ele expõe apenas `gate_id`, `execution_id`, `stage_id`, `decision`, critérios
atendidos/não atendidos e `evaluated_at`. `GateDecision` usa os valores
canônicos `APPROVED`, `APPROVED_WITH_PENDING` e `BLOCKED` em Python,
persistência, OpenAPI, HTTP e frontend.

O host registra explicitamente `project_id → project path`, com raízes
autorizadas opcionais e validação do manifesto. Requests não recebem paths; não
há glob, descoberta em tempo de request ou catálogo global mutável. A execução
é resolvida e validada antes da leitura dos gates, ocultando registros órfãos.
Falhas de projeto, execução e ownership compartilham resposta 404 segura;
falhas internas não expõem YAML, SQLite, parser ou paths.

`create_default_app()` e `create_default_operational_composition()` não expõem
essa rota. `create_sequential_operational_api_composition()` é a composição
opt-in e reutiliza uma única composição sequencial: o Orchestrator, o
`ExecutionState`, o resolver e o repository observados pela API pertencem ao
mesmo grafo e lifetime.

## Interface `/quality`

O dashboard agregado anterior foi preservado. O explorador sequencial começa
ocioso, exige IDs explícitos, codifica cada segmento da URL, mantém retry
isolado e distingue loading, 404, falha operacional, vazio e resultados.
Critérios são apresentados como critérios; a UI não inventa evidência, score,
severity, remediation, health ou readiness.

## Limitações e exclusões

- a API sequencial é opt-in e exige registros de projetos fornecidos pelo host;
- não há listagem pública de projetos ou execuções sequenciais;
- não há migração automática dos artefatos YAML históricos;
- o registro estruturado e o YAML não possuem atomicidade cross-store;
- resultados órfãos permanecem armazenáveis, mas não são publicamente
  consultáveis sem a execução canônica;
- Intelligent Orchestration não foi conectada a este fluxo;
- a Fase 23 não unifica `Run`, `SequentialExecution` e `ProjectExecution`;
- no Windows, um teste legado de multiprocessing pode falhar com `WinError 5`
  ao criar named pipe; essa falha ambiental deve ser classificada separadamente.

## Evidências de fechamento da Sprint 23.4

Em 2026-08-11, 74 testes backend focados passaram. A suíte Python coletou
1.272 testes: 1.269 passaram, 2 foram ignorados e somente o caso legado de
multiprocessing falhou por `WinError 5`; com esse caso desmarcado, todo o
restante passou. `compileall` foi aprovado.

No frontend, 26 arquivos e 139 testes passaram; TypeScript, lint e build
Next.js foram aprovados. O build gerou 11 páginas estáticas e confirmou
`/quality`. Os checks de whitespace do diff também foram aprovados.

## Rastreabilidade

A decisão de identidade, fonte da verdade, persistência e autorização está no
[ADR-033](../adr/ADR-033-sequential-quality-boundary.md). O estado operacional
está em [PROJECT_STATE](../../project/PROJECT_STATE.md) e a continuidade em
[NEXT_STEPS](../../project/NEXT_STEPS.md).
