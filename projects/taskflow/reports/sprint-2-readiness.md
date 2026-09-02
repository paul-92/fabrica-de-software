# TaskFlow — Sprint 2 readiness

**ID:** TASKFLOW-SPRINT-2-READINESS | **Versão:** 1.2.0 | **Status:** revised — awaiting authorization
**Dono:** autoridade do projeto | **Data original:** 2026-08-29 | **Revisão:** 2026-09-02
**Project ID:** `9be00568-4026-4929-8abb-9933581c31bd`

## Atualização de interpretação — 2026-09-02

**Classificação da conclusão anterior:** **SUPERSEDED / REVISED**.

A versão 1.1.0 tratou `validation_strategy = null` na preparation como um gap
que, isoladamente, exigiria decisão antes de qualquer aprovação. Auditoria
posterior do modelo `ProjectExecution`, do fluxo de Project Engineering, dos
testes de compatibilidade e da persistência operacional confirmou que
`validation_strategy` é opcional durante preparation. No desenho atual, a
strategy estruturada é construída e persistida durante execution/validation;
quando o serviço estruturado não está disponível, permanece um fallback legado.

Portanto, `validation_strategy = null` durante preparation **não constitui,
sozinho, blocker** e não deve motivar uma correção artificial no fluxo de
preparation.

Esta revisão **não declara a Sprint 2 pronta, aprovada ou autorizada**. A
cobertura efetiva dos critérios, os validators/targets aplicáveis, os riscos de
dependência e migração e o Quality Gate ainda precisam ser comprovados no ciclo
apropriado. Approval e execution continuam dependentes de decisão humana
explícita. O restante deste documento é preservado como análise histórica; onde
houver conflito, esta atualização prevalece.

## Objetivo

Consolidar o handoff documental para a Sprint 2 sem iniciá-la, criar preparation
ou execution, aprovar dependências ou modificar o workspace do TaskFlow.

## Fontes auditadas em modo read-only

- registros oficiais do projeto, sessões e executions no armazenamento ASEP;
- plano incremental aprovado na sessão, registrado pela execution
  `2d1d16c2-af7f-4cb4-a78a-427344900b5d`;
- fechamento da Fase 0 registrado pela execution
  `8c511f9c-5968-4b63-9085-40080e9283e2` como `FASE 0: PASS`;
- preparation aprovada da Sprint 1, execution
  `6088e824-54b6-4519-a25b-de3569a0acda`;
- execution homologada da Sprint 1
  `fe0acdc7-210a-4631-8c16-1968563f0e4e`;
- `.asep/dependency-baseline.json`, manifests, lockfile, código, testes e
  configuração do workspace TaskFlow;
- [fechamento formal da Sprint 1](sprint-1-closure.md);
- validators allowlisted na implementação atual da ASEP.

## Classificação das informações

- **Fato documentado:** a Sprint 1 está concluída; sua execution homologada
  terminou com `succeeded` e Quality Gate `APPROVED`.
- **Decisão aprovada:** baseline funcional, arquitetura, plano incremental e
  ADRs 001–018 da Fase 0, conforme a homologação registrada na ASEP.
- **Inferência:** áreas prováveis de impacto e validators aplicáveis, derivados
  do escopo aprovado e da estrutura física atual. Não constituem autorização.
- **Informação ausente:** preparation operacional, dependency plan e validation
  strategy estruturados especificamente para a Sprint 2.

## Baseline não regressiva

A Sprint 2 deve preservar integralmente:

- monorepo npm com `apps/web`, `apps/api`, `apps/worker` e pacotes compartilhados;
- Next.js, React e TypeScript no frontend;
- NestJS com Fastify na API;
- worker NestJS e fundação BullMQ;
- Prisma e preparação de PostgreSQL;
- Redis e configuração local existente;
- `packages/config` e contratos entre workspaces;
- manifests com versões exatas, `package-lock.json` e provisioning estruturado;
- TypeScript estrito e os typechecks de API e worker já homologados;
- testes e configurações de build/qualidade existentes;
- validators allowlisted e Quality Gate obrigatório;
- isolamento arquitetural entre web, API, worker, persistência e contratos;
- nenhuma regressão nos resultados da execution homologada da Sprint 1.

## Sprint 2 — Banco, organizations, autenticação e usuários

### Objetivo aprovado

Entregar identidade, isolamento organizacional básico e acesso seguro ao
sistema.

### Escopo funcional aprovado

- organização inicial;
- login e logout, incluindo logout de todas as sessões;
- sessões opacas e revogáveis;
- convite de usuário e definição de senha pelo convidado;
- recuperação e redefinição de senha;
- criação, desativação e reativação de usuário pelo administrador;
- consulta e edição de perfil;
- bloqueio imediato do usuário desativado;
- papéis organizacionais `ADMIN` e `MEMBER`.

### Escopo técnico aprovado

- módulos de organizations, authentication, sessions, users, invitations,
  password recovery, profiles e authorization;
- identidade global `User`, e-mail normalizado globalmente único,
  `Organization` e `OrganizationMembership`;
- `organizationId` obrigatório e contexto organizacional derivado da sessão;
- senhas protegidas com Argon2id;
- tokens de convite e recuperação persistidos apenas como hash, com expiração,
  uso único e consumo atômico;
- sessões revogáveis e invalidadas na desativação, sem restauração na reativação;
- autorização aplicada no backend por membership ativa e papel;
- persistência PostgreSQL/Prisma e datas em UTC;
- e-mail transacional inicialmente por interface/fake;
- auditoria mínima de autenticação;
- frontend para login, convite, recuperação/redefinição, perfil e administração
  inicial de usuários.

### Fora de escopo

Tudo que o plano incremental atribui às Sprints 3–9, incluindo projetos,
membros de projeto, etiquetas, tarefas, subtarefas, comentários, workflow de
tarefas, notificações funcionais, dashboards, pesquisa, Kanban e produção.

### Requisitos e critérios de aceitação aprovados

- administrador cria ou convida usuários;
- convidado define a própria senha;
- usuário recupera a senha por fluxo seguro;
- usuário desativado perde acesso imediatamente;
- sessão pode ser revogada;
- membro não acessa funções administrativas;
- nenhuma consulta aceita `organizationId` arbitrário enviado pelo cliente;
- login válido e inválido são testados;
- desativação bloqueia acesso e revoga sessões;
- convites e recuperação cobrem expiração, uso único e replay;
- autorização administrativa e isolamento entre organizações são testados;
- perfil pode ser editado sem alterar o e-mail;
- fluxos E2E de login, convite e recuperação são testados;
- tokens, senhas e dados sensíveis não aparecem em logs.

### Critério de conclusão aprovado

Fluxos completos de autenticação e usuário passam em testes unitários, de
integração e E2E, incluindo casos negativos de autorização e tenancy, com
Quality Gate aprovado e sem regressão da Sprint 1.

## Decisões arquiteturais reutilizadas

- monólito modular com web, API e worker implantáveis separadamente;
- REST JSON e OpenAPI;
- PostgreSQL como fonte oficial, Prisma e migrações controladas;
- identidade global e memberships organizacionais;
- autenticação por e-mail/senha, Argon2id e sessões opacas revogáveis;
- autorização obrigatória no backend;
- isolamento por `organizationId` em consultas, comandos e constraints;
- bootstrap administrativo idempotente, transacional e alimentado por secrets;
- concorrência otimista e atomicidade transacional;
- outbox/eventos versionados e idempotência quando aplicáveis;
- timezone IANA por organização, instantes persistidos em UTC;
- preservação indefinida de dados empresariais e auditoria;
- logs correlacionados sem secrets.

## ADR-014 resolvido

A autoridade do projeto aprovou **convite/token de ativação de uso único** e
rejeitou a alternativa de senha inicial via secret com troca obrigatória. O
contrato completo foi materializado em
[`ADR-014-bootstrap-initial-credentials.md`](../decisions/ADR-014-bootstrap-initial-credentials.md).

O bloqueio arquitetural está resolvido. A decisão não autoriza execution.

## Preparation estruturada

- preparation ID: `ac47bfaf-b2b2-4772-b5ec-9f943535557f`;
- status: `pending`;
- sprint ID: `2`;
- sprint name: `Banco, organizations, autenticacao e usuarios`;
- engineering phase: `development`;
- autorização de uma preparation: **CONSUMIDA**;
- execution: **NÃO CRIADA / NÃO AUTORIZADA**;
- DeveloperAgent, provisioning e validators: **NÃO EXECUTADOS**.

## Dependências aprovadas e materializadas

| Package | Version | Manifest group | Status |
|---|---:|---|---|
| `@nestjs/common` | `11.2.3` | dependencies | APPROVED |
| `@nestjs/core` | `11.2.3` | dependencies | APPROVED |
| `@nestjs/platform-fastify` | `11.2.3` | dependencies | APPROVED |
| `@prisma/client` | `7.10.0` | dependencies | APPROVED |
| `bullmq` | `6.3.1` | dependencies | APPROVED |
| `fastify` | `5.12.1` | dependencies | APPROVED |
| `next` | `16.3.3` | dependencies | APPROVED |
| `react` | `19.2.8` | dependencies | APPROVED |
| `react-dom` | `19.2.8` | dependencies | APPROVED |
| `prisma` | `7.10.0` | devDependencies | APPROVED |
| `typescript` | `5.9.3` | devDependencies | APPROVED |
| `@types/node` | `24.13.3` | devDependencies | APPROVED |
| `@taskflow/config` | `0.1.0` | workspace dependency | NOT APPLICABLE — pacote interno |

Nenhuma versão existente foi alterada. O lockfile contém dependências
transitivas, mas presença transitiva não equivale a aprovação para uso direto.

### Novas dependências após a preparation

O dependency plan estruturado da preparation reutilizou somente as dependências
já aprovadas e materializadas. Não foi criado dependency request novo. Portanto:

- dependências novas identificadas: **0**;
- decisão humana de dependência pendente: **nenhuma gerada pelo fluxo**;
- aprovação automática: **PROIBIDA**;
- capacidades de Argon2id e testes continuam sem pacote externo específico
  selecionado; uma execution não pode inferir ou instalar pacote fora do plano.

## Mapa de impacto provável

Esta seção é inferencial e não autoriza mudanças.

| Área | Motivo | Requisito | Risco | Baseline a preservar |
|---|---|---|---|---|
| `apps/api` | endpoints, guards e módulos de identidade | auth/users/orgs | fuga de tenant ou autorização inconsistente | NestJS/Fastify, contratos e typecheck |
| `apps/web` | telas e fluxos de acesso/perfil | login, convite, recuperação | exposição de dados ou contrato divergente | Next.js/React e build |
| `prisma` / futura fronteira database | entidades e migrações | User, Organization, Membership, Session e tokens | migração irreversível ou constraint incompleta | Prisma/PostgreSQL e schema validável |
| `packages/config` | secrets, TTLs e bootstrap | configuração segura | segredo em log ou startup permissivo | fail-fast e contratos existentes |
| futuros packages compartilhados | contratos e authorization | DTOs/políticas | acoplamento ou modelo Prisma exposto | fronteiras do monorepo |
| `tests` | unidade, integração, E2E e isolamento | critérios de aceite | falso positivo sem dois tenants | testes existentes e casos negativos |
| `apps/worker` | somente se o desenho autorizado encaminhar e-mail assíncrono | interface/fake transacional | antecipar Sprint 6 | BullMQ sem jobs de negócio |
| infra/config de bootstrap | primeira org e admin | bootstrap idempotente | credencial vazada ou duplicação | secrets externos e idempotência |

## Plano de validação

### Validação existente na ASEP

- `workspace_changes` e `idempotent_state`;
- `typecheck`;
- `vitest`;
- `eslint`;
- `next_build`;
- Quality Gate `PROJECT-ENGINEERING-VALIDATION`.

### Validação provavelmente aplicável

- `workspace_changes` para evidência das alterações autorizadas;
- `typecheck` nos targets afetados da API, web, worker e packages;
- `next_build` para alterações no frontend;
- `vitest` se um script/configuração suportado for materializado por decisão
  aprovada;
- `eslint` se um script/configuração suportado for materializado;
- Quality Gate obrigatório após todos os validators selecionados.

### Validação não definida na strategy atual

- validator dedicado de Prisma/migrações;
- testes de integração PostgreSQL;
- testes E2E de login, convite e recuperação;
- matriz negativa com duas organizações;
- varredura específica de tokens/senhas em logs;
- teste concorrente/idempotente do bootstrap;
- smoke de revogação imediata de sessões.

Essas provas são exigidas pelo plano, mas seu mapeamento para validators
allowlisted não foi produzido pela preparation estruturada. A resposta da
preparation não contém validation strategy, validators ou targets. Validators
não podem ser desativados nem substituídos por declaração textual.

## Riscos e pendências comprovadas

- o ADR-014 foi resolvido por convite/token de ativação de uso único;
- o dependency plan da Sprint 2 existe e contém apenas dependências aprovadas;
- nenhuma dependência nova foi identificada pelo fluxo;
- a preparation não produziu validation strategy estruturada;
- a ASEP não possui validators dedicados para todas as provas de aceitação
  previstas no plano;
- o workspace atual possui somente `packages/config`; as demais fronteiras
  compartilhadas planejadas ainda precisam de decisão/materialização;
- o schema Prisma atual é apenas estrutural e não contém o domínio da Sprint 2;
- `apps/worker` não deve receber jobs funcionais de notificação/e-mail da Sprint
  6 por antecipação;
- qualquer execução deve preservar os typechecks homologados da API e worker,
  manifests exatos, lockfile, provisioning e Quality Gate da Sprint 1.

## Governança e readiness

| Item | Classificação | Motivo |
|---|---|---|
| Baseline da Sprint 1 | READY | Homologada e encerrada |
| Requisitos da Sprint 2 | READY | Plano incremental aprovado |
| Arquitetura geral | READY | Fase 0 `PASS` e ADRs 001–018 aprovados |
| Credencial concreta do bootstrap | READY | Convite/token de ativação de uso único aprovado |
| Dependency plan da Sprint 2 | READY | Criado; somente dependências aprovadas, sem itens novos |
| Validation strategy da Sprint 2 | INFORMATION REQUIRED | Não foi criada pela preparation |
| Autorização de preparation | READY | Concedida e integralmente consumida |
| Autorização de execution | APPROVAL REQUIRED | Não concedida |

**[HISTÓRICO — SUPERSEDED / REVISED] READINESS: C — VALIDATION GAP REQUIRES DECISION**

A Sprint 2 permanece **BLOQUEADA PARA EXECUÇÃO**. Além de não existir
autorização de execution, os critérios sem cobertura precisam de tratamento
explícito antes de qualquer aprovação da preparation.

## Handoff

- preparation nova: **sim — uma, autorização consumida**;
- preparation ID: `ac47bfaf-b2b2-4772-b5ec-9f943535557f`;
- preparation status: `pending`;
- execution nova: **não**;
- Sprint 2 iniciada: **não**;
- workspace TaskFlow modificado: **não**;
- dependency baseline modificado: **não**;
- SQLite modificado: **não**;
- validators executados: **não**;
- commit: **não**;
- push: **não**.

## Próxima ação exata

A autoridade do projeto deve decidir como os critérios sem cobertura serão
mapeados para validações automatizadas allowlisted antes de aprovar a
preparation; nenhuma execution deve ser criada.
