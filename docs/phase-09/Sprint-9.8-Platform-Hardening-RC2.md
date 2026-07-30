# Sprint 9.8 — Platform Hardening & Release Candidate 2

**Público:** engenharia, QA, segurança e responsáveis pelo release  
**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** tecnicamente validada; revisão humana e publicação pendentes  
**Data da evidência:** 2026-07-30

## Objetivo

Consolidar a arquitetura da Fase 9 sem adicionar funcionalidade. A revisão
abrangeu código, dependências, segurança, testes, documentação, exemplos,
observabilidade, persistência, pipeline e API pública.

## Entradas e método

Foram inspecionados `src/asep`, `tests`, `examples`, `pyproject.toml`, README,
mapas, estado, roadmap, histórico, ADRs 016–028 e documentos das Sprints
8.6–9.7. A análise usou AST da biblioteca padrão, buscas com `rg`, execução dos
gates e revisão manual das fronteiras críticas.

Ambiente observado: branch `feature/phase-9-intelligent-agents`, commit base
`f6ed7a1328acf32b0b4d0f530e91005725111e0b`, Windows, Python 3.14.4 64-bit.
O estado avaliado inclui mudanças locais ainda não versionadas.

## Auditoria arquitetural

- 179 módulos Python, 433 classes, 756 funções/métodos e 30 Protocols;
- zero ciclos de import entre módulos `asep`;
- a fachada `asep.execute` delega composição ao `PipelineBuilder`;
- Workflow, Planning, Coordination, Supervisor, Runtime, Tools e Memory
  permanecem separados por contratos;
- Coordinator executa agentes apenas pelo `AgentRuntime`;
- Supervisor decora o Runtime e não invade Planning ou Workflow;
- Tools ficam atrás do Registry e do serviço que aplica política e isolamento;
- repositories concretos continuam concentrados na composition root/factory.

Não foi encontrada violação que justifique refatoração de produção nesta
Sprint. Os maiores arquivos continuam sendo dívida conhecida, não evidência
isolada de defeito:

| Arquivo | Linhas |
|---|---:|
| `agents/execution_service.py` | 693 |
| `orchestrator/service.py` | 565 |
| `application/stage_execution.py` | 424 |
| `pipeline/pipeline.py` | 423 |
| `execution_graph/builder.py` | 403 |

Extrações futuras exigem caso de uso e testes próprios; reduzir linhas não é
critério suficiente.

## Auditoria de código e API

- nenhum `TODO`, `FIXME`, `HACK` ou `NotImplementedError` em produção;
- `asep.execute(goal, workspace, metadata, options)` é a fachada pública da
  Fase 9 e retorna `GoalResult`;
- modelos públicos continuam tipados e serializáveis;
- nenhum import dinâmico, `eval`, `exec`, `shell=True` ou shell genérico foi
  encontrado em produção;
- a execução de processo permanece isolada em `providers/process.py`;
- não foram removidas APIs nem alterado comportamento externo.

Foram corrigidos somente fatos documentais obsoletos. Nenhum código de produção
foi alterado no hardening.

## Auditoria de dependências

As dependências diretas possuem uso comprovado: Typer/Rich na CLI, Pydantic em
contratos, PyYAML em loaders/estado, Jinja2 no agente determinístico, FastAPI e
Uvicorn na API, pytest/pytest-cov/HTTPX nos testes. `pip check` retornou
`No broken requirements found`.

Permanece o risco de reprodutibilidade por ausência de lockfile. Os intervalos
do `pyproject.toml` são deliberados e nenhuma biblioteca foi atualizada nesta
Sprint.

## Auditoria de segurança

Controles confirmados:

- `MemoryFilter` remove chaves sensíveis e padrões textuais antes de persistir;
- resultados, exceções e eventos evitam detalhes de credenciais nos caminhos
  cobertos por testes;
- Tools resolvem caminhos contra o workspace e rejeitam traversal;
- execução de subprocesso usa lista de argumentos, timeout, captura e
  `shell=False`;
- serializers aceitam somente valores JSON;
- SQLite usa parâmetros e as escritas file usam substituição atômica;
- `.env`, bancos, storage, logs e temporários estão cobertos pelo `.gitignore`.

Riscos residuais:

| Risco | Severidade | Condição de encerramento |
|---|---|---|
| filtro lexical não reconhece todo segredo sem marcador | média | classificação de dados e scanner especializado |
| metadados válidos podem carregar conteúdo sensível | média | revisão no produtor e política de schema |
| SQLite local não é criptografado | média conforme o dado | proteção do filesystem/armazenamento externo |
| histórico Git não passou por scanner dedicado | média | scanner antes da publicação |
| Tool de testes inicia subprocesso autorizado | baixa | manter allowlist, timeout e `shell=False` |

## Observabilidade, persistência e recuperação

Timeline e métricas cobrem Workflow, Planning, Coordination, Agent, Tool,
Memory e Recovery. Falhas supervisionadas são representadas por resultado
tipado; retry/fallback emitem eventos. Backends memory, file e SQLite mantêm
testes de contrato. Persistência do pipeline da Fase 9 continua deliberadamente
em memória na composição padrão; retomada automática do novo pipeline não faz
parte do RC2.

## Testes e exemplos

| Evidência | Resultado |
|---|---:|
| testes coletados/aprovados | 794/794 |
| cobertura total | 95% (`7.748` statements, `416` não cobertos) |
| módulos `test_*.py` | 53 |
| `compileall src tests examples` | aprovado |
| exemplos executados | 3/3 |
| `pip check` | aprovado |
| `git diff --check` | aprovado, com avisos CRLF |

O primeiro pytest dentro do sandbox encontrou `PermissionError` no basetemp do
Windows. A repetição fora dessa ACL, ainda usando basetemp no workspace,
aprovou todos os testes. Isso é limitação ambiental reproduzível, não falha do
produto.

## Problemas encontrados e tratamento

1. `PROJECT_STATE` registrava branch e commit antigos: corrigido.
2. `NEXT_STEPS` proibia iniciar uma Sprint já autorizada: corrigido.
3. Roadmap atribuía RC2 à Sprint 9.6 e listava Claude Provider sem
   implementação: corrigido.
4. README apontava apenas para RC1: atualizado para o RC2.
5. índices não continham a consolidação 9.4–9.8: atualizados.
6. 4.062 arquivos temporários de pytest permanecem rastreados no commit base:
   não foram removidos do índice, pois essa decisão de versionamento é humana.

## Decisão e gate

**Decisão técnica:** RC2 aprovado tecnicamente com pendências operacionais.

Não há bloqueador funcional conhecido. A publicação permanece pendente de:

- revisão humana do diff acumulado;
- remoção intencional dos temporários rastreados em mudança própria;
- commits/push autorizados;
- CI ou clone limpo em Windows e ao menos um sistema POSIX;
- scanner de segredos no histórico;
- decisão explícita sobre lockfile;
- tag criada somente pela autoridade de release.

## Checklist

- [x] arquitetura, código, dependências e segurança auditados;
- [x] observabilidade, persistência, pipeline e API revisados;
- [x] documentação e exemplos revisados;
- [x] Release Notes, Migration Guide e diagrama oficial atualizados;
- [x] ADR Index revisado; nenhum ADR novo necessário;
- [x] testes, cobertura, compileall, pip check e diff check aprovados;
- [ ] revisão humana;
- [ ] worktree versionado e limpo;
- [ ] validação remota/clone limpo;
- [ ] publicação/tag.

## Referências

[Release Candidate 2](../releases/ReleaseCandidate2.md),
[Migration Guide RC2](../migration/MigrationGuide-RC2.md),
[Architecture Map](../architecture/ArchitectureMap.md),
[ADR-028](../adr/ADR-028-end-to-end-pipeline.md) e
[Project State](../../project/PROJECT_STATE.md).
