# Project Sessions and Execution History

**Dono:** Engenharia ASEP | **Versão:** 0.4 | **Status:** vigente

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
única observabilidade de continuidade anterior; a versão 0.3 acrescenta
`context_char_count` e `context_omitted_execution_count`. Apenas essas métricas
são persistidas; o prompt/contexto integral não é duplicado. Payloads antigos
carregam defaults seguros.

Isolamento por projeto e sessão é obrigatório. O workspace permanece a fonte
da verdade do estado físico atual; mudanças históricas são apenas evidência e
nunca reconstroem arquivos.

### Budget e compactação determinística

`SessionContextPolicy` é o budget único: 8 entries, 20.000 caracteres totais,
2.000 por instruction, 4.000 por summary, 50 changes por entry e 500 por path.
A unidade de `context_char_count` é a quantidade de caracteres Unicode do JSON
canônico provider-agnostic completo de `AIRuntimeRequest.context`, incluindo a
chave `project_session` (`sort_keys`, UTF-8 legível e separadores compactos).
Esse tamanho inclui chaves/labels JSON, delimitadores, IDs, status, flags,
`error_code`, paths e contadores de omissão.

O pipeline é `history elegível → projeção segura → ContextCompactor →
SessionRuntimeContext`. Entries recentes têm prioridade. Dentro de uma entry,
o compactor tenta preservar outcome/instruction e changes antes do summary:
remove summary, omite changes pela cauda determinística e somente então reduz
instruction pelo maior prefixo que cabe. Se nem o núcleo couber, omite a entry.
`omitted_change_count`, `context_omitted_execution_count` e flags de truncation
impedem que compactação pareça conteúdo completo.

Não há deduplicação, resumo por IA, tokens estimados ou seleção semântica.
Mesmo history e policy produzem exatamente o mesmo JSON.

## Memória durável da sessão

`ProjectExecution History`, `SessionRuntimeContext`, `SessionMemory` e workspace
são conceitos distintos. History é auditoria; recent context é uma projeção
efêmera; memory guarda fatos duráveis selecionados da sessão; o workspace é a
fonte da verdade para o código atual. A memória não é uma thread do Codex e não
é compartilhada entre sessões ou projetos.

`SessionMemoryEntry` é imutável e provider-agnostic. Entradas manuais têm
`source_execution_id = null`; a extração automática, sem IA, cria apenas
`artifact` para `WorkspaceChange created` de uma execução bem-sucedida. Não há
NLP heurístico, embeddings, busca semântica ou resolução de contradições.

O backend limita cada conteúdo a 2.000 caracteres, considera as 50 entradas
mais recentes e limita a projeção enviada ao runtime a 8.000 caracteres.
Igualdade normalizada exata por projeto, sessão, tipo e conteúdo é deduplicada.
Contradições permanecem em ordem determinística. A prioridade é: instrução
atual, workspace, contexto recente e memória da sessão.

Somente `memory_entry_count`, `memory_char_count` e `memory_truncated` ficam na
execução. O prompt final e a projeção completa não são persistidos. Registros
antigos usam `0`, `0` e `false`.

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
implementações em memória e SQLite. `SessionMemoryRepository` segue a mesma
fronteira, com implementações InMemory e SQLite. SQLite usa o banco ASEP existente, tabelas
aditivas com foreign keys para `projects` e `project_sessions`, e payload JSON
determinístico validado novamente pelos modelos na leitura. Nenhum reset ou
migration destrutiva é executado.
