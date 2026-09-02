# AI HANDOFF — ASEP

> **DOCUMENTAÇÃO É CONTEXTO. O ESTADO EXECUTÁVEL É A FONTE FINAL DA VERDADE.**
>
> Leia [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) para arquitetura, decisões,
> histórico e rationale. Este arquivo é o checkpoint operacional.

## Checkpoint

| Campo | Valor auditado em 2026-09-02 |
|---|---|
| Branch | `feature/phase-10-business-engineering` |
| HEAD | `ce6d08608067b37a07b1330b3ce3048f2abaeb34` |
| Working tree | Clean antes da criação deste draft documental |
| Remote | Ref local `origin/feature/phase-10-business-engineering` coincide com HEAD |
| Upstream | Não configurado |
| Fetch | Não executado; sincronização remota não foi comprovada pela rede |

## Active Project

- Project: **TaskFlow Beta Test**
- Project ID: `9be00568-4026-4929-8abb-9933581c31bd`
- Workspace: `C:\Users\paulo.trajano\ASEP-Beta\workspaces\legacy-local\9be00568-4026-4929-8abb-9933581c31bd\workspace`
- Operational storage: `C:\Users\paulo.trajano\ASEP-Beta\data`

Os caminhos são específicos do ambiente Windows atual e precisam ser
redescobertos em outro host.

## Current Sprint

**Sprint 2 — Banco, organizations, autenticação e usuários**

- **[NÃO AUTORIZADO] PREPARED/PENDING**
- **NOT EXECUTED**
- **NOT AUTHORIZED FOR APPROVAL OR EXECUTION**
- Preparation: `ac47bfaf-b2b2-4772-b5ec-9f943535557f`

Preparation não é execution. Presença de planos não concede autoridade.

## Last Completed Actions

- **[VALIDADO]** Sprint 1 homologada com Quality Gate `APPROVED`.
- **[HISTÓRICO]** 4.062 artefatos temporários Pytest deixaram de ser rastreados em `3d0f331`.
- **[VALIDADO]** Prefixo acidental de `developer.py` removido cirurgicamente em `ce6d086`.
- **[VALIDADO]** Auditoria documental/read-only concluída.
- **[VALIDADO]** Repositório estava limpo antes deste draft documental.

## Runtime

- API: **STOPPED** no checkpoint; nenhum listener na porta `8000`.
- Não assumir que processos sobrevivem entre sessões.
- Comando documentado, a executar somente quando autorizado:

```powershell
python -m uvicorn asep.api.composition:create_default_app --factory --host 127.0.0.1 --port 8000
```

Health:

```text
GET http://127.0.0.1:8000/api/v1/health
```

## Persisted Sprint 2 State

Confirmado em leitura SQLite `mode=ro` durante a auditoria porque a API estava
parada:

| Campo | Valor |
|---|---|
| `status` | `pending` |
| `error_code` | `null` |
| `blocker` | `null` |
| `next_action` | `null` |
| `operational_plan` | present |
| `preparation_analysis` | present |
| `dependency_plan` | 23 entries; todas `approved` |
| `validation_strategy` | `null` |
| `validations` | absent |
| `step_results` | absent |
| Sprint 2 provisioning | absent |
| `repair` | absent |
| `quality_gate` | absent |

Consulta futura deve preferir o endpoint governado, não escrita/acesso direto ao
banco.

## Important Architectural Clarification

> **[VALIDADO]** `validation_strategy = null` durante preparation é válido no
> desenho atual. A strategy estruturada é construída e persistida durante
> execution/validation; existe fallback legado.

Isso remove um falso blocker, mas **não** prova coverage, readiness ou aprovação
da Sprint 2.

## Active Decisions

- Efeitos de agentes são mediados por Tools governadas.
- Planejamento precede execução consequencial.
- Dependências externas exigem versões exatas e decisão governada.
- Provisioning aceita somente dependency plan integralmente aprovado.
- Package interno (`@taskflow/config`) não é dependência externa.
- Argon2id é requisito; nenhum package Argon2 foi selecionado.
- Repair é separado de retry/recovery operacional.
- Quality Gate permanece separado do provider/agente e exige evidence.
- Bootstrap TaskFlow usa invite/one-time activation token, nunca senha inicial distribuída.
- A timing atual de `validation_strategy` não deve ser alterada sem decisão arquitetural.

## Immediate Risks

- `git status` emite `Permission denied` para diretórios ignorados:
  - `.pytest-codex-dependency-reuse/`;
  - `.pytest-retomada-focused/`;
  - `test-output/dependency-reuse/`.
- Não tratar automaticamente esses avisos como corrupção do Git.
- O schema Prisma já contém `Task`, embora tasks estejam fora da Sprint 2.
- A branch não possui upstream e não houve `fetch` de rede.
- Runtime e estado persistido podem divergir deste checkpoint em sessão futura.

## DO NOT

- Não aprovar nem executar a Sprint 2 automaticamente.
- Não chamar POST de prepare, approve, execute, cancel ou dependency version sem autoridade explícita.
- Não instalar dependências fora da governança; não escolher package Argon2 por inferência.
- Não executar migrations destrutivas ou editar SQLite diretamente.
- Não desativar validators, contornar Quality Gate ou transformar texto em evidence.
- Não alterar silenciosamente ADRs ou decisões protegidas.
- Não usar `git add .` em working tree misturada.
- Não limpar, restaurar ou descartar mudanças desconhecidas.
- Não fazer commit, push, merge ou alterar `main` sem autorização específica.
- Não registrar tokens, hashes, senhas ou secrets em logs/documentos.

## Exact Next Step

Próxima sequência, ainda sem autorização para approve/execute:

1. confirmar Git/branch/HEAD;
2. verificar runtime/processos;
3. iniciar API somente com autorização operacional;
4. conferir health;
5. ler a preparation da Sprint 2 pelo GET oficial;
6. comparar resposta com persistência e este handoff;
7. revisar dependency plan, operational plan e coverage esperada;
8. reavaliar readiness;
9. pedir decisão humana antes de qualquer approval/execution.

## Read-only Target

```text
GET /api/v1/projects/9be00568-4026-4929-8abb-9933581c31bd/executions/ac47bfaf-b2b2-4772-b5ec-9f943535557f
```

Base local histórica: `http://127.0.0.1:8000`.

## Important IDs

| Item | ID |
|---|---|
| TaskFlow project | `9be00568-4026-4929-8abb-9933581c31bd` |
| Sprint 1 homologated execution | `fe0acdc7-210a-4631-8c16-1968563f0e4e` |
| Sprint 2 preparation | `ac47bfaf-b2b2-4772-b5ec-9f943535557f` |
| Phase 0 closure | `8c511f9c-5968-4b63-9085-40080e9283e2` |

## Important Paths

| Caminho | Uso |
|---|---|
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Memória estrutural oficial |
| [AGENTS.md](../AGENTS.md) | Contrato operacional e autoridade |
| [TaskFlow README](../projects/taskflow/README.md) | Índice documental do projeto |
| [Sprint 1 closure](../projects/taskflow/reports/sprint-1-closure.md) | Homologação da Sprint 1 |
| [Sprint 2 readiness](../projects/taskflow/reports/sprint-2-readiness.md) | Readiness e revisão histórica |
| [TaskFlow ADR-014](../projects/taskflow/decisions/ADR-014-bootstrap-initial-credentials.md) | Bootstrap por activation token |
| [ADR-034](../docs/adr/ADR-034-controlled-approved-dependency-provisioning.md) | Provisioning governado |
| `src/asep/application/project_engineering_execution.py` | Construção/persistência da validation strategy |
| `src/asep/projects/history_models.py` | Contrato de `ProjectExecution` |
| `src/asep/application/project_ai_runtime.py` | Preparation, dependency plan e execução preparada |

## Useful Commands

### Read-only

```powershell
git status --short --branch
git branch --show-current
git log -1 --format="%H %s"
git diff --stat
git diff --cached --stat
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
curl.exe --silent --show-error http://127.0.0.1:8000/api/v1/health
curl.exe --silent --show-error http://127.0.0.1:8000/api/v1/projects/9be00568-4026-4929-8abb-9933581c31bd/executions/ac47bfaf-b2b2-4772-b5ec-9f943535557f
```

### State-changing — require separate authorization

Starting the API changes runtime state; approval/execution/dependency POSTs,
installations, migrations, commits, pushes and merges require their own explicit
authority. Do not keep ready-to-run POST commands in the handoff.

## Proceed Criteria

Consider asking for Sprint 2 approval only when:

- branch/HEAD/worktree are understood;
- API and official GET reproduce the expected preparation;
- preparation remains `pending` and unconsumed;
- no real blocker/error/new dependency decision is pending;
- operational and dependency plans match approved scope;
- Argon2/package decision is handled through governance if needed;
- validation expectations have an evidence-producing path;
- migration/data/security risks are explicit;
- the authorized human receives the readiness analysis.

Meeting these conditions permits a decision; it does not auto-authorize execution.

## Stop / Escalate Criteria

Stop on unexpected branch/HEAD, unknown dirty tree, changed preparation status,
new external dependency, destructive migration, ADR change, gate bypass, secret,
architecture change, inconsistent Quality Gate, data-loss risk or request to
alter `main`. Follow [core/ESCALATION.md](../core/ESCALATION.md).

## Provider Resume Protocol

1. Read `PROJECT_CONTEXT.md`.
2. Read this handoff.
3. Read `AGENTS.md` and applicable local rules.
4. Confirm task objective, scope and authority.
5. Run Git status, branch and HEAD checks.
6. Do not clean or restore unknown changes.
7. Check processes/API; never assume runtime persistence.
8. Read current project/preparation state.
9. Compare current facts with this checkpoint.
10. Report divergences and risks.
11. Inspect dependency and validation implications.
12. Propose the smallest safe next action.
13. Wait for human authority at consequential gates.

**Never continue mechanically from the next checklist item without validating
the real state.**

## Update Rule

Atualize este arquivo quando houver mudança importante de branch/HEAD, avanço
de Sprint, início/fim de execution, Quality Gate, blocker, dependency decision,
mudança arquitetural, incidente ou alteração material do próximo passo. Preserve
o contexto durável em `PROJECT_CONTEXT.md` e registre fatos históricos sem
reescrita silenciosa.
