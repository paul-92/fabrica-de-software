# Fase 23 — Projeções operacionais públicas

**Público:** produto, engenharia, arquitetura, qualidade e operações

**Dono:** Engenharia ASEP

**Versão:** 1.2

**Status:** em andamento; Sprints 23.1–23.6 concluídas

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

A Sprint 23.6 está formalmente encerrada. A Fase 23 continua em andamento e
incrementos posteriores dependem de priorização explícita.

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
- no Windows, um teste legado de multiprocessing pode falhar com `WinError 5`
  ao criar named pipe; essa falha ambiental deve ser classificada separadamente.

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
