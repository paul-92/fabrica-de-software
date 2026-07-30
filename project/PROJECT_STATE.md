# Estado atual da ASEP

**Atualizado em:** 2026-07-30  
**Projeto:** AI Software Engineering Platform (ASEP)  
**Versão do pacote:** 0.1.0

## Propósito

Plataforma local para workflows de engenharia de software assistidos por
agentes, com contratos, execução, artefatos, gates, observabilidade e
persistência.

## Estado de entrega

- Fase 6: concluída;
- Fase 7: concluída até SQLite;
- Fase 8: concluída localmente;
- Sprint 8.1: implementada e validada localmente;
- Sprint 8.2: implementada e validada localmente, ainda pendente de commit;
- Sprint 8.3: implementada e validada localmente, ainda pendente de commit;
- Sprint 8.4: implementada e validada localmente, ainda pendente de commit;
- Sprint 8.5: implementada e validada localmente, ainda pendente de commit;
- Sprint 8.6: hardening concluído localmente; RC1 pendente de publicação;
- Sprint 9.1: Intelligent Agent Runtime implementado localmente;
- Sprint 9.2: Tool Contracts & Tool Registry implementada localmente;
- Sprint 9.3: Agent Memory & Context Management implementada localmente;
- Sprint 9.4: Planning Engine implementado localmente.
- Sprint 9.5: Multi-Agent Coordination implementada localmente.
- Sprint 9.6: Intelligent Execution & Recovery implementada localmente;
- Sprint 9.7: End-to-End Execution Pipeline implementado localmente.
- Sprint 9.8: Platform Hardening concluído e RC2 tecnicamente validado;
  revisão humana e publicação pendentes.

O commit base avaliado é
`f6ed7a1328acf32b0b4d0f530e91005725111e0b`. A árvore possui mudanças locais
acumuladas das Fases 8 e 9. Não migre confiando apenas no remoto antes de
revisão, commit e push autorizados.

## Git

- branch principal remoto: `main`;
- branch de trabalho: `feature/phase-9-intelligent-agents`;
- remote: `origin`;
- versão local está à frente do remote branch e contém mudanças não commitadas.

## Arquitetura

Monólito modular Python. Principais módulos: `application`, `orchestrator`,
`execution`, `workflow`, `runtime`, `providers`, `artifacts`, `quality`,
`runs`, `timeline`, `repositories`, `configuration`, `sqlite`, `metrics`,
`api`, `execution_graph` e `exporters`.
O pacote `agents` expõe contratos formais, Registry em memória e runtime
inteligente independente de provider. O Workflow Engine chega ao runtime
somente por `AgentStepAdapter`.
O pacote `tools` expõe contratos, Registry, execução observável e Tools
restritas ao workspace.
O pacote `memory` expõe memória operacional, stores em memória/SQLite, retenção,
filtragem e ContextBuilder.
O pacote `planning` expõe plano imutável, estratégia sequencial, políticas,
validação, Timeline e métricas, sem executar Tools.
O pacote `agents.coordination` distribui planos por capability, assignments e
fila sequencial, delegando execução exclusivamente ao Agent Runtime.
O pacote `runtime.recovery` fornece Supervisor compatível com AgentRuntime,
máquina de estados, classificação, retry, backoff, fallback e observabilidade.
O pacote `pipeline` fornece ASEPEngine, composição padrão e GoalResult,
integrando o fluxo completo por `asep.execute`.

Persistência: memory, file JSON e SQLite. Integrações: Codex por subprocess,
CLI Typer, FastAPI, Mermaid, BPMN e JSON.

Há dois limites distintos:

- `Orchestrator` de projetos ASEP;
- `WorkflowOrchestrator` genérico, que delega ao `WorkflowEngine`.

## Comandos

```text
python -m pip install -e ".[test]"
asep --help
asep run projects/asep-self-development
asep resume RUN_ID
asep runs
python -m uvicorn asep.api.composition:create_default_app --factory
python -m pytest -v
```

## Evidência

Python validado: 3.14.4 64-bit no Windows. Suporte declarado: `>=3.12`.
Suíte: 794 testes aprovados e cobertura global arredondada de 95% (7.748
statements, 416 não cobertos). `compileall`, exemplos, `pip check` e
`git diff --check` aprovados no gate final da Sprint 9.8.

## Pendências e limitações

- revisão, commit e push autorizados das mudanças acumuladas;
- sem lockfile: dependências usam intervalos no `pyproject.toml`;
- workflow genérico apenas síncrono/sequencial;
- sem retry, timeout, paralelismo ou subworkflows no Engine genérico;
- nenhum agente autônomo novo foi criado;
- Agent Runtime é síncrono; timeout não interrompe chamada bloqueada;
- idempotência e métricas do runtime são somente em memória;
- Tool Registry, métricas e idempotência também são somente em memória;
- nenhuma autorização granular por agente foi implementada para Tools;
- backend `file` usa MemoryStore volátil;
- filtragem não reconhece segredo sem marcador textual;
- Agent Registry é somente em memória, sem discovery ou persistência;
- Workflow Persistence possui memory/file/sqlite, mas não permite retomada;
- RC2 ainda depende de revisão humana, decisão sobre temporários rastreados,
  commit/push, clone limpo, CI e scanner de histórico;
- backend padrão em memória;
- SQLite sem migrations, pool ou backup automático;
- divergências históricas listadas em Architecture v1.

## Decisões essenciais

ADRs 016–028: SQLite; Orchestrator; Engine; Agents; Workflow Persistence;
Intelligent Agent Runtime; Tool Registry; Agent Memory; Planning Engine;
Multi-Agent Coordination; Execution Recovery; End-to-End Pipeline.
Sprint 8.6 não criou ADR por não alterar decisão arquitetural.

## Leitura essencial

[Bootstrap](../BOOTSTRAP.md), [Next Steps](NEXT_STEPS.md),
[Architecture v1](../docs/architecture/ASEP-Architecture-v1.md),
[Roadmap](../docs/architecture/Roadmap.md),
[Documentation Index](../docs/DocumentationIndex.md) e
[Current Sprint Prompt](../prompts/CurrentSprintPrompt.md).
