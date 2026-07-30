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
- Sprint 9.2: não iniciada.

O último commit local é `863766f` (Sprint 7.5) e ainda não consta no remote
tracking branch. A árvore possui mudanças da Fase 8. Não migre confiando apenas
no remoto antes de commit/push.

## Git

- branch principal remoto: `main`;
- branch de trabalho: `feature/sprint-3-core-architecture`;
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

Python validado: 3.14.4 64-bit no Windows 11. Suporte declarado: `>=3.12`.
Suíte: 684 testes aprovados e cobertura global de 95%. `compileall`, links e
`git diff --check` integram o gate final da Sprint.

## Pendências e limitações

- commit/push da Fase 8 e push do commit 7.5;
- sem lockfile: dependências usam intervalos no `pyproject.toml`;
- workflow genérico apenas síncrono/sequencial;
- sem retry, timeout, paralelismo ou subworkflows no Engine genérico;
- nenhum agente autônomo novo foi criado;
- Agent Runtime é síncrono; timeout não interrompe chamada bloqueada;
- idempotência e métricas do runtime são somente em memória;
- Agent Registry é somente em memória, sem discovery ou persistência;
- Workflow Persistence possui memory/file/sqlite, mas não permite retomada;
- RC1 ainda depende de commit/push, clone limpo, CI e scanner de histórico;
- backend padrão em memória;
- SQLite sem migrations, pool ou backup automático;
- divergências históricas listadas em Architecture v1.

## Decisões essenciais

ADRs 016–022: SQLite; Orchestrator; Engine; Agents; Workflow Persistence;
Intelligent Agent Runtime.
Sprint 8.6 não criou ADR por não alterar decisão arquitetural.

## Leitura essencial

[Bootstrap](../BOOTSTRAP.md), [Next Steps](NEXT_STEPS.md),
[Architecture v1](../docs/architecture/ASEP-Architecture-v1.md),
[Roadmap](../docs/architecture/Roadmap.md),
[Documentation Index](../docs/DocumentationIndex.md) e
[Current Sprint Prompt](../prompts/CurrentSprintPrompt.md).
