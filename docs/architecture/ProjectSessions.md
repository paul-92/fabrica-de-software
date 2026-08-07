# Project Sessions and Execution History

**Dono:** Engenharia ASEP | **Versão:** 0.1 | **Status:** vigente

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
