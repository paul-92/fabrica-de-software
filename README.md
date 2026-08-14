# AI Software Engineering Platform — ASEP

**Versão documental:** 0.1.0
**Status:** implementação funcional até a Fase 22; gate frontend final pendente
**Dono:** Product Manager da ASEP

A ASEP é uma plataforma local para desenvolvimento de software assistido por
agentes. Ela combina governança, workflows, execução, providers, artefatos,
quality gates, persistência, Timeline, métricas e observabilidade.

## Como funciona

Uma demanda é registrada pelo Intake, classificada pelo Orchestrator e associada a um workflow. Cada etapa recebe agentes cujo contrato declara entradas, saídas, limites e gates. Artefatos permanecem no projeto; decisões duráveis usam ADR; aprovações humanas e eventos mantêm a rastreabilidade. O funcionamento central está em [core/SYSTEM.md](core/SYSTEM.md).

## Estrutura principal

| Área | Responsabilidade |
|---|---|
| `core/` | funcionamento, governança, lifecycle, qualidade e segurança |
| `roles/`, `departments/` | autoridade organizacional e especialidades |
| `agents/`, `contracts/` | comportamento e interfaces dos agentes |
| `registry/` | catálogo e descoberta dos componentes |
| `workflows/` | ordem, condições, gates e aprovações |
| `playbooks/` | procedimentos operacionais |
| `knowledge/` | conhecimento de negócio e engenharia |
| `standards/` | regras obrigatórias, recomendações e exceções |
| `templates/` | modelos de artefatos |
| `clients/`, `projects/` | contexto segregado de clientes e iniciativas |
| `memory/` | aprendizado global validado |
| `observability/` | eventos, métricas, auditoria e status |
| `orchestrator/`, `runtime/` | especificação da execução futura |
| `planning/`, `reports/` | evolução da plataforma e auditoria |

## Fluxo de um projeto

Intake → Discovery → Business Analysis → Architecture → Planning → Design → Implementation → Review → Testing → Security → Deployment → Documentation → Handover → Maintenance → Retrospective. Etapas podem ser condicionais ou paralelas conforme o workflow, mas gates não são omitidos.

## Como iniciar

Para preparar uma máquina limpa, siga o [BOOTSTRAP.md](BOOTSTRAP.md). Para
continuar o desenvolvimento, consulte o
[estado atual](project/PROJECT_STATE.md), os
[próximos passos](project/NEXT_STEPS.md) e o
[checklist de migração](project/MIGRATION_CHECKLIST.md).
O estado do candidato atual está em
[Release Candidate 2](docs/releases/ReleaseCandidate2.md). O
[RC1](docs/releases/ReleaseCandidate_RC1.md) permanece como registro histórico.
O empacotamento de processos para a VM Linux do Private Beta está no
[runbook de deployment](deployment/README.md).

1. Leia [VISION.md](VISION.md), [AGENTS.md](AGENTS.md) e [core/SYSTEM.md](core/SYSTEM.md).
2. Copie `clients/_template/` se houver novo cliente.
3. Copie `projects/_template/` e preencha `project.yaml` e o Project Brief.
4. Execute [workflows/project-intake.md](workflows/project-intake.md).
5. Selecione um workflow registrado em [registry/workflows.yaml](registry/workflows.yaml).
6. Registre decisões materiais em `projects/<id>/decisions/`.

### Executar o núcleo 0.1

Requer Python 3.12 ou superior. No diretório do repositório:

```bash
python -m venv .venv
python -m pip install -e ".[test]"
asep run projects/asep-self-development
```

O comando cria um `run_id`, executa o workflow, persiste
estado e logs e aciona o runtime configurado. Artefatos ficam em
`projects/<id>/artifacts/runs/<run_id>/`. Uma execução bloqueada ou com falha pode
ser retomada entre etapas com `asep resume <run_id>`. O núcleo genérico de
workflow atual é síncrono e sequencial; não há execução distribuída.

### Executar um objetivo pelo pipeline oficial

```python
import asep

result = asep.execute(
    goal="Analise este projeto e explique sua arquitetura.",
    workspace=".",
)
print(result.summary)
```

O pipeline integra Workflow, Planning, Coordination, Supervisor, Runtime,
Tools, Memory, Timeline e métricas. Veja o
[Getting Started](docs/examples/GettingStarted.md).

### Analisar um projeto deterministicamente

```python
from pathlib import Path
from asep.project_analysis import ProjectAnalyzer

analysis = ProjectAnalyzer().analyze(Path("."))
print(analysis.languages)
```

O [Project Analyzer](docs/project-analysis/Overview.md) identifica estrutura,
tecnologias, dependências, arquitetura e estatísticas sem IA ou integração com
o Agent Runtime.

## Como criar um novo agente

Use [templates/agent.md](templates/agent.md), mantenha as 27 seções obrigatórias, crie o contrato correspondente, registre ambos em `registry/agents.yaml` e `registry/contracts.yaml`, valide conflitos de autoridade e obtenha aprovação conforme [core/GOVERNANCE.md](core/GOVERNANCE.md).

## Como criar um novo workflow

Use um workflow YAML existente como referência, declare dependências, condições, gates, aprovações, artefatos e falhas; registre em `registry/workflows.yaml`; valide agentes e gates; aprove a mudança segundo [core/CHANGE-MANAGEMENT.md](core/CHANGE-MANAGEMENT.md).

## Como criar um novo projeto

Copie `projects/_template/`, atribua ID único em `kebab-case`, escolha `project_type` e `workflow_id` existentes, mantenha artefatos no próprio projeto e use `artifacts/` apenas para ativos globais aprovados.

## Navegação complementar

O material anterior útil foi preservado em `docs/`, `prompts/` e nos playbooks por tipo de produto. Use o [índice da documentação ASEP](docs/DocumentationIndex.md) como ponto de entrada. O [inventário de ambiente](project/ENVIRONMENT_INVENTORY.md) registra requisitos não sensíveis. O glossário histórico está em [docs/glossary.md](docs/glossary.md) e os termos de persistência em [docs/glossary/PersistenceGlossary.md](docs/glossary/PersistenceGlossary.md). Decisões humanas abertas estão em [reports/open-decisions.md](reports/open-decisions.md).

Os contratos e o catálogo em memória de agentes da Fase 8 estão documentados
em [Agent Contracts](docs/workflows/AgentContracts.md) e
[Agent Registry](docs/workflows/AgentRegistry.md).
O runtime inteligente da Fase 9, com política, validação, Timeline, métricas e
integração ao Workflow Engine, está em
[Agent Runtime](docs/agents/AgentRuntime.md).
A infraestrutura oficial de capacidades reutilizáveis está em
[Tool Architecture](docs/tools/ToolArchitecture.md).
A memória operacional e o contexto reutilizável estão em
[Agent Memory](docs/agents/AgentMemory.md).
Snapshots completos de execução são descritos em
[Workflow Persistence](docs/workflows/WorkflowPersistence.md).
O pipeline consolidado e a geração determinística validada estão descritos em
[Fase 15](docs/phase-15/intelligent-orchestrator.md) e
[Fase 16](docs/phase-16/software-generation-validation.md).
A camada visual e white-label está descrita na
[Fase 22](docs/phase-22/white-label-presentation-layer.md).

## Contributing

Contributions are welcome. Please open an Issue before creating a Pull Request.
