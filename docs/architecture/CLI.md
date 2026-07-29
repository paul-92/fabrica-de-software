# CLI

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

O entry point `asep = asep.cli:app` usa Typer. Mensagens operacionais usam
stderr quando o stdout precisa permanecer consumível por pipelines.

## Comandos

| Comando | Responsabilidade |
|---|---|
| `asep run PROJECT` | cria UUID v4, configura log e inicia execução |
| `asep resume RUN_ID` | localiza `state.yaml` no workspace e retoma |
| `asep graph PROJECT` | carrega workflow, constrói grafo estático e exporta |
| `asep runs` | lista Runs disponíveis no processo atual |
| `asep run show RUN_ID` | mostra detalhes de um Run |
| `asep run timeline RUN_ID` | mostra a Timeline de um Run |

Opção `--verbose/-v` existe em `run` e `resume`.

## Graph

```text
asep graph PROJECT [--format mermaid|bpmn] [--output/-o PATH] [--force]
```

Mermaid é o formato padrão. Sem `--output`, apenas o documento gerado é escrito
no stdout. Com arquivo, a confirmação vai para stderr. Qualquer extensão é
aceita sem renomear ou alertar.

```bash
asep graph projects/asep-self-development
asep graph projects/asep-self-development --format bpmn
asep graph projects/asep-self-development --format bpmn -o workflow.bpmn
asep graph projects/asep-self-development -o workflow.mmd --force
```

A escrita cria o diretório pai e um temporário curto no mesmo filesystem.
Sem `--force`, `os.link` fornece criação exclusiva; com `--force`, `os.replace`
substitui atomicamente. Falhas removem o temporário.

```mermaid
sequenceDiagram
    participant U as Usuário
    participant C as CLI graph
    participant L as Loaders
    participant G as ExecutionGraphBuilder
    participant E as Exporter
    U->>C: project, format, output
    C->>L: carregar e validar
    C->>G: build(workflow)
    G-->>C: ExecutionGraph
    C->>E: export(graph)
    E-->>C: string
    C-->>U: stdout ou arquivo atômico
```

## Erros

Erros esperados descendem de `AsepError`, possuem código e exit code e são
impressos sem traceback. Validação de opções do Typer retorna código diferente
de zero antes de criar saída. O CLI não executa Codex real no comando `graph`.

## Histórico de Runs

```text
asep runs [--status pending|running|succeeded|failed|cancelled]
asep run show RUN_ID
asep run timeline RUN_ID
```

Os comandos usam `RunQueryService`; consulta e formatação permanecem separadas.
Runs são exibidos do mais recente para o mais antigo. Timelines são exibidas em
ordem cronológica. Datas usam ISO 8601, campos ausentes usam `-`, metadata usa
JSON com chaves ordenadas e Runs ativos mostram duração `running`.

O parser de `run` preserva `asep run PROJECT` e reserva as ações `show` e
`timeline` para consultas hierárquicas. Não existem aliases planos. Um Run
inexistente produz `RUN_NOT_FOUND`, stderr e exit code 2. Uma lista ou Timeline
vazia é uma consulta válida e retorna exit code zero.

Os repositories atuais são somente em memória e ainda não são alimentados pelo
lifecycle de execução. Assim, processos independentes da CLI não compartilham
histórico e normalmente iniciam vazios. Consulte
[Run Query Service](RunQueryService.md); não há persistência durável nesta
versão.

## Adicionar comando

1. componha APIs públicas existentes;
2. use tipos e validação Typer;
3. mantenha conteúdo de pipeline no stdout e operação no stderr;
4. converta erros esperados pelo padrão `AsepError`;
5. reutilize escrita segura quando produzir arquivo;
6. acrescente testes com `CliRunner`;
7. não replique lógica de domínio ou de exporter.
