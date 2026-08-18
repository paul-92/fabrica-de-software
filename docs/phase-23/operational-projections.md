# Fase 23 — Projeções operacionais públicas

**Público:** produto, engenharia, arquitetura, qualidade e operações

**Dono:** Engenharia ASEP

**Versão:** 1.3

**Status:** concluída; Sprints 23.1–23.8 encerradas em 2026-08-12

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
- **23.5:** consultas avançadas e autorizadas de Session Memory, com paridade
  InMemory/SQLite, API pública paginada e busca operacional em `/knowledge`.
- **23.6:** Runtime Branding canônico e persistente, projeção pública read-only,
  consumo resiliente no App Shell e administração somente por composição
  confiável, sem mutação HTTP.
- **23.7:** primeiro vertical Project Engineering operacional: tarefa, plano,
  mutação confinada, diff, validação, repair limitado, Quality Gate,
  memória/histórico e projeção API/UI sob uma única `ProjectExecution`.
- **23.8:** auditoria arquitetural, regressão econômica e sincronização
  documental de fechamento.

**PHASE 23 — COMPLETED.** O fechamento não afirma autonomia geral nem que todos
os agentes e fluxos da ASEP sejam operacionais ponta a ponta.

## Marco operacional — Project Engineering

O primeiro vertical operacional comprovado da ASEP é Project Engineering:

```text
tarefa → plano bounded → runtime → mutação do workspace → diff
→ pytest → repair opcional (máximo 1) → pytest final → Quality Gate
→ memória/histórico → API pública → /projects
```

`ProjectEngineeringExecutionService` coordena portas Application. A composição
constrói e compartilha repositories de projeto, sessão, execução e memória,
runtime, snapshot/diff, `RunTestsTool`, repair, `QualityGateEngine` e
`QualityGateResultRepository`. Não há singleton, service locator ou extração de
dependências por `app.state`; o adapter HTTP recebe o serviço Application.

Uma única `ProjectExecution` nasce antes da mutação e mantém o mesmo
`execution_id` no plano, diff, validações, repair, Quality Gate, memória,
histórico e DTO público. Nesse bounded context, o `run_id` do resultado de
Quality Gate recebe explicitamente `ProjectExecution.execution_id`; isso não o
transforma em `Run` ou `SequentialExecution`. Sucesso exige validação final
verde e gate não bloqueado; `BLOCKED` nunca é projetado como sucesso.

O endpoint legado de AI runtime foi preservado. `read_only` continua no fluxo
anterior; somente `workspace_write` usa o orchestrator de engenharia. O painel
em `/projects` exibe plano, mudanças, validações, repair e gate por DTOs do
cliente HTTP, sem importar internals Python.

### Acceptance/E2E comprovado

`tests/qa/api/test_project_engineering_operational_composition.py` cria projeto
e sessão descartáveis, usa fake apenas no boundary do runtime externo e mantém
composição real abaixo dele. O fake altera arquivos reais da fixture; o fluxo
real calcula diff, executa pytest por `RunTestsTool`, avalia e persiste o gate,
registra memória/histórico e devolve a mesma execução por HTTP. Há ainda caminho
de validação falha, repair único, segunda falha e gate `BLOCKED`. O teste não
substitui cada camada por mocks e confirma que nenhum `Run` ou
`SequentialExecution` é criado.

## Metodologia de testes da Fase 23

| Tipo | Exemplo real | Prova | Não prova |
|---|---|---|---|
| Unitário | `test_project_engineering_validation_repair.py` | regra isolada, output bounded e repair máximo 1 | wiring HTTP ou persistência real |
| Contrato/modelo | `test_branding_repository.py` e modelos de `ProjectExecution` | strict/frozen, invariantes e defaults | integração entre componentes |
| Paridade de repository | `test_quality_gate_result_repository.py` e `test_session_memory_query.py` | semântica Memory/File/SQLite suportada e reconstrução | operação distribuída/transacional |
| Application | `test_project_engineering_execution.py` | orchestration, ordem, identidade e estados finais | serialização/OpenAPI |
| API/OpenAPI | `test_project_engineering_operational_composition.py` | mapping público, campos bounded e compatibilidade | comportamento visual no browser |
| Fronteira arquitetural | testes de source/import em API e frontend | ausência de imports proibidos | correção funcional completa |
| Composition/shared lifetime | compositions de Branding e Project Engineering | identidade compartilhada e isolamento | concorrência entre processos |
| Componente frontend | `ProjectRuntimePanel.test.tsx` e `QualityWorkspace.test.tsx` | estados e projeção visual acessível | servidor/API reais |
| Service/client | `knowledge.test.ts`, `branding.test.ts`, `sequentialQuality.test.ts` | URL, encoding, DTO e erros HTTP | renderização React |
| Acceptance/E2E | `test_http_acceptance_task_to_public_result_uses_one_execution` | vertical real abaixo do fake externo | Codex real, cloud ou produção |
| Segurança/erros | cross-project, cursor, path confinement e erro sanitizado | ownership e não vazamento conhecido | threat model completo/pentest |

Fakes implementam um boundary determinístico, como o runtime externo no
Acceptance; stubs fornecem respostas predeterminadas; mocks verificam
interações. São úteis em testes focados, mas trocar todas as camadas por mocks
deixa de provar composição, filesystem, pytest, persistência e serialização.

Uma suite **focused** cobre o slice alterado; uma **regression** acrescenta
consumidores e contratos vizinhos; a **complete suite** cobre o repositório todo
e é reservada para risco proporcional. `compileall` detecta sintaxe/imports;
`typecheck`, contratos TypeScript; `lint`, regras estáticas; o build Next.js,
compilação de produção e rotas; `git diff --check`, whitespace; auditoria
OpenAPI, o schema público. Nenhum gate isolado prova o comportamento E2E.

Falha funcional reproduz defeito do produto; falha ambiental impede o gate por
restrição externa. O `WinError 5` em named pipes de multiprocessing e o
`spawn EPERM` em workers Vite são exemplos ambientais em Windows restrito.
Devem ser registrados e rerodados em ambiente apto, nunca tratados
silenciosamente como sucesso.

## Runtime Branding — Sprint 23.6

O branding institucional canônico contém somente `product_name`, `short_name`,
`logo_url`, `workspace_label` e `footer_text`. `BrandingRepository` armazena um
snapshot completo ou ausência de override, com implementações InMemory, File e
SQLite selecionadas pela `RepositoryFactory`. O formato File é versionado e usa
substituição atômica; SQLite usa uma linha singleton no banco compartilhado.

`BrandingQueryService` resolve o override completo ou
`DEFAULT_BRANDING_SETTINGS`, sem merge parcial e sem persistir defaults. A
projeção pública é:

```text
GET /api/v1/branding
```

O adapter HTTP conhece somente Application e expõe os cinco campos
institucionais. Não há POST, PUT, PATCH ou DELETE de branding.

No frontend, o `BrandConfig` de deployment continua sendo renderizado no HTML
inicial. Após hidratação, um único owner no `AppShell` consulta o endpoint pelo
service/API client e substitui somente identidade institucional. Loading, erro
e retry preservam o fallback build-time; token monotônico impede resposta
antiga. Favicon, metadata, `defaultTheme`, cores e a preferência `asep-theme`
continuam fora do contrato runtime.

`BrandingAdministrationService` executa substituição completa validada pelo
modelo canônico. `create_trusted_branding_administration_composition()` entrega
ao host o `app` e o command service, sem colocá-lo em `app.state` ou expô-lo por
HTTP. Query e administração recebem exatamente
`repositories.branding_repository` do mesmo `RepositoryBundle`; composições
independentes permanecem isoladas.

### Decisão de segurança

A mutação HTTP e a UI administrativa ficam **adiadas** até existir uma
fronteira real de autenticação e autorização. A Sprint 23.6 não inventa usuário,
role, RBAC ou permissão. CORS não é tratado como autenticação. Esse adiamento
não é pendência para o fechamento da vertical read-only/trusted-host.

Estado das slices:

- 23.6A Architecture/Audit — concluída;
- 23.6B Persistence — concluída;
- 23.6C Public Read API — concluída;
- 23.6D Runtime Frontend Consumption — concluída;
- 23.6E Trusted Administration — concluída.

Esta vertical poderá ser usada posteriormente na apostila para explicar
Dependency Injection, Repository Pattern, Application Services, Composition
Root, shared lifetime/identity, DTO versus Domain Model, fallback/resiliência,
fronteiras read/write, segurança por não exposição e taxonomia de testes. A
apostila não faz parte da Sprint 23.6.

## Advanced Knowledge Queries — Sprint 23.5

O fluxo read-only implementado é:

```text
HTTP → SessionMemorySearchService → ProjectSessionService.get(project, session)
→ SessionMemoryQuerySource → InMemory/SQLite → resposta paginada → /knowledge
```

`SessionMemoryQuerySource` é separado do contrato legado de comandos, mas o
`RepositoryBundle` atribui ambos ao mesmo objeto:

```python
bundle.session_memory_repository is bundle.session_memory_query_source
```

Assim, uma escrita por `ProjectSessionMemoryService` fica imediatamente
visível na consulta sem cache, cópia ou segundo store. No backend `file`, esta
família continua honestamente InMemory; somente SQLite oferece durabilidade.

A autorização ocorre antes da query. `ProjectSessionService.get()` é a fonte
canônica para existência do projeto, existência da sessão e ownership. Sessão
ausente e sessão de outro projeto compartilham semântica pública segura, e uma
memória órfã não autoriza uma sessão inexistente.

A busca é substring determinística sobre conteúdo com trim, collapse de
whitespace e casefold. `kind` usa somente `SessionMemoryKind`. A ordenação total
é `(created_at, memory_id)`, descendente para `newest` e ascendente para
`oldest`, inclusive para instantes equivalentes com offsets diferentes.

A paginação é keyset, não offset. O cursor URL-safe/Base64 contém versão,
projeto, sessão, texto normalizado, kind, ordem, timestamp e `memory_id`; é
opaco para Application, HTTP e frontend. Ele não é assinado nem criptografado.
Cursores incompatíveis falham de forma tipada. O contrato limita páginas a
`1..100`, usa 25 por padrão, não fornece `total_count` e não promete snapshot
transacional diante de inserções concorrentes.

O endpoint aditivo é:

```text
GET /api/v1/projects/{project_id}/sessions/{session_id}/memory/search
```

Ele aceita `text`, `kind`, `order`, `page_size` e `cursor`, e responde somente
com `items` e `next_cursor`. Cada item expõe os sete fatos já públicos de
`SessionMemoryEntry`. GET e POST legados em `/memory` permanecem sem paginação
e sem mudança de envelope.

No frontend, `ProjectHistoryClient` usa path IDs codificados e
`URLSearchParams`; React não usa `fetch` diretamente. `/knowledge` mantém o
percurso Projeto → Sessão, carrega a primeira página sem exigir texto, permite
filtros explícitos e adiciona páginas sem duplicar `memory_id`. Um token
monotônico impede respostas antigas de projeto, sessão, busca ou load-more de
contaminar o estado atual. Falha de load-more preserva itens e possui retry
isolado.

### Evidências e taxonomia de testes da vertical

- unitários e contract tests: modelos frozen/strict, defaults e limites;
- repository parity e reconstruction: mesma semântica InMemory/SQLite e reopen;
- ownership e negative/security: validação antes da query, cross-project,
  órfãos, cursores incompatíveis e caracteres SQL tratados literalmente;
- API, OpenAPI e architectural boundary: DTO exato, respostas 200/400/404/422/500
  e rota sem imports de repository/storage;
- composition/shared identity: command/query no mesmo objeto e composições
  isoladas;
- compatibility/regression: endpoints `/memory`, AI Runtime, Planning,
  Intelligent Integration e Agent Memory preservados;
- frontend service, stale-response e accessibility: URL encoding,
  `URLSearchParams`, paginação, retry, labels, `status` e `alert`;
- gates: suíte Python e frontend, compileall, typecheck, lint, production build
  e `git diff --check`.

Falhas ambientais são separadas de produto: o teste legado de multiprocessing
pode receber `WinError 5` em named pipes no Windows restrito; Vite pode receber
`spawn EPERM` ao iniciar workers no mesmo tipo de sandbox. Reruns fora dessas
restrições comprovam independência da vertical.

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
- o plano Project Engineering é determinístico e bounded, não generativo;
- o Acceptance automatizado usa fake do boundary Codex;
- não há multi-agent operacional completo, rollback automático, execução
  distribuída, produção/cloud ou observabilidade externa;
- repair permanece limitado a uma tentativa neste vertical;
- não existe auth/RBAC nem mutação administrativa HTTP de branding;
- no Windows, um teste legado de multiprocessing pode falhar com `WinError 5`
  ao criar named pipe; essa falha ambiental deve ser classificada separadamente.

## Evidências de fechamento da Fase 23

Na entrega 23.7D, 164 testes backend passaram. No fechamento 23.8, uma regressão
focada ampliada aprovou 290 testes backend. O frontend final aprovou 28 arquivos
e 164 testes, typecheck, lint e build; `/projects` foi gerada. `compileall`,
referências Markdown e `git diff --check` foram aprovados. São gates focados na
Fase 23 e consumidores, não uma nova suite Python completa.

## Direção pós-Fase 23

A próxima fase deve aprofundar engenharia de software: decomposição e
planejamento mais ricos, `DeveloperAgent` operacional, tarefas multi-step,
seleção de validação mais precisa, repair mais inteligente, coordenação
multi-agent controlada e acceptance em projetos reais maiores.

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
