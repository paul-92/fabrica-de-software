# Project Sessions and Execution History

**Dono:** Engenharia ASEP | **Versão:** 0.2 | **Status:** vigente

## Objetivo

`ProjectSession` agrupa trabalho lógico dentro de um `WorkspaceProject`.
Ela não representa nem armazena a sessão de autenticação ChatGPT/Codex.

```text
WorkspaceProject 1 ── * ProjectSession 1 ── * ProjectExecution
                                                │
                                                ├─ AIRuntimeUsage real
                                                ├─ WorkspaceChange observado
                                                └─ error_code seguro
```

Uma execução exige `session_id` explícito. A Application Layer valida que a
sessão pertence ao projeto antes de resolver o workspace ou chamar o runtime.
O browser continua sem autoridade para fornecer `workspace_path`, `cwd` ou
sandbox.

## Continuidade de contexto

Histórico auditável e contexto de runtime são representações distintas.
`SessionContextBuilder` projeta somente campos seguros de execuções anteriores
concluídas (`succeeded` ou `failed`) do mesmo projeto e da mesma
`ProjectSession`: identificador, instrução, status, output normalizado como
summary opcional, `error_code` seguro e mudanças reduzidas a path/tipo.
Execuções `pending`/`running`, usage, modelo, runtime, timestamps, metadata,
stderr e conteúdo de arquivos não entram no contexto.

A projeção `SessionRuntimeContext` é efêmera, provider-agnostic e limitada por
8 entries, 2.000 caracteres por instrução, 4.000 por summary e 20.000
caracteres textuais totais, além de limites defensivos para changes. Os itens mais
recentes têm prioridade e são entregues em ordem narrativa. Ela é serializada
em `AIRuntimeRequest.context.project_session`; não é persistida como uma cópia
do histórico e não cria/reutiliza thread ou session do Codex.

O contexto é construído antes de persistir a execução corrente, que nunca
entra no próprio contexto. `context_entry_count` e `context_truncated` são a
única observabilidade adicional persistida; o prompt/contexto integral não é
duplicado. Payloads anteriores à versão 0.2 carregam defaults `0` e `false`.

Isolamento por projeto e sessão é obrigatório. O workspace permanece a fonte
da verdade do estado físico atual; mudanças históricas são apenas evidência e
nunca reconstroem arquivos.

## Histórico auditável

Antes da chamada síncrona, a execução é persistida como `running`. Ela é
finalizada como `succeeded` ou `failed`. Sucesso preserva output normalizado,
runtime, modelo, usage real e evidências de mudanças. Falha preserva apenas um
`error_code` seguro e eventuais mudanças observadas após falha parcial; stderr,
mensagens externas brutas, credenciais e conteúdo de arquivos não são salvos.

Listagens retornam itens mais recentes primeiro. O histórico é somente para
consulta: ele não dispara replay, retry, rollback ou execução automática.

## Persistência

Os contratos `ProjectSessionRepository` e `ProjectExecutionRepository` têm
implementações em memória e SQLite. SQLite usa o banco ASEP existente, tabelas
aditivas com foreign keys para `projects` e `project_sessions`, e payload JSON
determinístico validado novamente pelos modelos na leitura. Nenhum reset ou
migration destrutiva é executado.
