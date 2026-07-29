# Execution

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Responsabilidades

### ExecutionBootstrap

Carrega projeto, localiza a raiz, carrega Registry e workflow, verifica
aplicabilidade, valida com `SequentialWorkflowEngine`, monta paths, cria
`RunContext` e solicita ao `StateManager` o estado `created`. Em `resume`,
recarrega e reconcilia o estado existente sem criar outro run.

### Orchestrator

É o coordenador: inicia ou retoma, mantém o loop, aplica transições, salva o
estado e decide concluir, bloquear ou falhar. Ele não constrói prompt/pacote,
não executa subprocess e não persiste conteúdo de artefato.

### StageExecutionService

Monta o `AgentContext`; executa pelo `AgentRuntime` quando não há provider ou
constrói prompt e pacote para o `AgentProvider` injetado; normaliza o resultado;
persiste artefatos somente após sucesso; avalia e persiste o quality gate.
Retorna `StageExecutionReport` sem transicionar estados.

## Nova execução

```mermaid
sequenceDiagram
    participant CLI
    participant B as ExecutionBootstrap
    participant O as Orchestrator
    participant S as StateManager
    participant W as WorkflowEngine
    participant E as StageExecutionService
    CLI->>B: prepare(project_path, run_id)
    B->>S: create(state=created)
    B-->>O: project, registry, workflow, context, state
    O->>S: created -> ready -> running
    loop enquanto houver etapa elegível
        O->>W: next_stage
        O->>S: pending -> ready -> running
        O->>E: execute_stage
        E-->>O: StageExecutionReport
        O->>S: completed, blocked ou failed
    end
    O->>S: running -> completed
```

## Retomada

`resume(state_path)` preserva o `run_id`, recarrega projeto/Registry/workflow e
valida a identidade. `StateManager.prepare_resume` aceita apenas execuções
`failed` ou `blocked`, transiciona a execução para `running` e o loop seleciona
a primeira etapa não concluída. Etapas `completed` são terminais e não são
executadas novamente.

Apesar de a tabela de transições permitir `awaiting_approval → running`, a API
de retomada atual rejeita esse estado. Não existe nesta versão um comando de
aprovação humana.

## Estados

```mermaid
stateDiagram-v2
    [*] --> created
    created --> ready
    ready --> running
    running --> awaiting_approval
    running --> blocked
    running --> failed
    running --> cancelled
    running --> completed
    awaiting_approval --> running
    awaiting_approval --> blocked
    awaiting_approval --> cancelled
    blocked --> running
    blocked --> cancelled
    failed --> running
    failed --> cancelled
    cancelled --> [*]
    completed --> [*]
```

Etapas seguem máquina equivalente, com `pending → ready → running` e estados
terminais adicionais `skipped`, `cancelled` e `completed`. Cada transição gera
`TransitionRecord`. O snapshot YAML é validado antes de `os.replace`.

## Persistência e riscos

- estado: `<project>/.asep/runs/<run_id>/state.yaml`;
- artefatos: `<project>/artifacts/runs/<run_id>`;
- logs: `<project>/logs/runs/<run_id>.jsonl`;
- pacotes, quando `ExecutionPackageWriter` é chamado explicitamente:
  `<project>/.asep/runs/<run_id>/packages/<stage_id>`.

Não há lock ou controle otimista entre processos. Duas retomadas simultâneas do
mesmo run podem perder atualizações; a operação atômica protege o arquivo contra
escrita parcial, não contra concorrência lógica.
