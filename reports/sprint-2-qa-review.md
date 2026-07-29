# Revisão Independente de QA — Sprint 2

**Projeto:** ASEP Self-development  
**Público:** Product Owner, Quality Lead, Software Architect e Engineering  
**Dono:** QA independente da Sprint 2  
**Versão:** 1.0.0  
**Status:** final — `BLOCKED`  
**Data:** 2026-07-29

## 1. Resumo executivo

**Classificação final: `BLOCKED`.**

O caminho feliz funciona: a suíte original passa em raiz curta, o Business
Analyst é determinístico, o workflow piloto executa uma etapa, o gate resulta em
`APPROVED`, artefatos e logs recebem o `run_id`, e a execução real
`b8732fb4-cba8-4a90-a99d-3c05cf013658` terminou `completed`.

Entretanto, evidências independentes reproduzem violações centrais:

1. não há lock single-writer; dois processos entram na retomada do mesmo run;
2. dois escritores válidos perdem atualização e histórico;
3. não há coerência obrigatória entre estado global e etapas;
4. estado aceita referência de artefato de outra execução/projeto;
5. sidecar de metadados pode ser sobrescrito e checksum não é verificado;
6. ADR-006 não implementa versão, `last_event_id`, intent/outcome, marker,
   reconciliação ou audit trail;
7. `awaiting_approval` não pode ser resolvido/retomado conforme ADR-009;
8. três testes E2E falham em caminho longo realista no Windows.

Os itens 1–6 criam risco de corrupção, falsa conclusão e perda de
rastreabilidade. A existência prévia desses débitos em relatórios não equivale a
aprovação ou exceção formal.

## 2. Commit e ambiente avaliados

| Item | Evidência |
|---|---|
| Commit | **não verificável**: `.git/` não está presente e `git` não está disponível no PATH |
| Data da revisão | 2026-07-29 |
| SO | Microsoft Windows `10.0.26200.8655`, 64 bits |
| Python | 3.14.4 em `.venv` |
| pytest | 8.4.2 |
| Pydantic | 2.13.4 |
| Typer | 0.27.0 |
| PyYAML | 6.0.3 |
| Rich | 14.3.4 |
| Jinja2 | 3.1.6 |
| dependências | `pip check`: nenhum conflito |

**Risco de baseline:** sem commit não é possível provar que a versão revisada
corresponde a uma revisão imutável. Condição obrigatória para nova avaliação:
fornecer SHA e worktree limpa ou manifest de fontes com hashes.

## 3. Documentos e ADRs consultados

Foram lidos:

- `AGENTS.md`, `README.md`, `VISION.md`, `WORKFLOW.md`;
- `core/COMMUNICATION.md`, `core/ESCALATION.md`, `core/QUALITY.md`,
  `core/LIFECYCLE.md`;
- `contracts/qa-engineer.yaml`, `roles/quality-assurance.md`;
- `standards/testing.md`, `standards/definition-of-done.md`,
  `standards/architecture.md`;
- `projects/asep-self-development/project.yaml`, brief, README e artefatos de
  Business Analysis;
- ADR-001 a ADR-014, com análise detalhada do ADR-014;
- `workflows/asep-self-development-sequential.yaml`,
  `workflows/software-project.yaml` e `registry/workflows.yaml`;
- `reports/sprint-2-implementation-report.md`,
  `reports/sprint-2-test-report.md`, `reports/sprint-2-open-issues.md`,
  `reports/sprint-1-qa-review.md`;
- `backlog/technical-debt.md`;
- toda a implementação em `src/asep/` e todos os testes em `tests/`.

Contradições documentais observadas:

- `project.yaml` marca Sprint 2 como `completed`, mas o gate de implementação
  está `pending` e esta QA estava pendente;
- o README do projeto ainda diz “sem Runtime” e “aguardando aprovações”;
- o relatório de implementação reconhece lock, audit trail e aprovação humana
  como não implementados, embora ADRs aceitos os tornem decisões obrigatórias.

## 4. Comandos executados

```powershell
python --version
python -m pytest
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest --basetemp <raiz-longa-no-workspace>
.\.venv\Scripts\python.exe -m pytest --basetemp C:\qa-asep\existing
.\.venv\Scripts\python.exe -m pytest tests\qa --basetemp C:\qa-asep\independent -q
.\.venv\Scripts\python.exe -m pytest --basetemp C:\qa-asep\all --cov=asep --cov-report=term-missing
.\.venv\Scripts\python.exe tools\validate-asep.py
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\asep.exe run projects\asep-self-development
.\.venv\Scripts\asep.exe resume b8732fb4-cba8-4a90-a99d-3c05cf013658
```

Observações:

- o Python global é 3.11.9 e não possui Typer; a execução correta requer a
  `.venv` 3.14.4;
- o validador documental foi impedido por `PermissionError` ao enumerar
  diretórios temporários inacessíveis deixados pelas primeiras execuções de
  pytest. Compilação e `pip check` passaram.

## 5. Testes existentes

Em raiz curta: **38 aprovados, 0 falhas, 5.14 s**.

Em raiz longa sob o workspace: **35 aprovados, 3 falhas, 4.99 s**. Falharam as
jornadas CLI/E2E de run e resume com `ARTIFACT_ERROR` por caminho temporário longo.

A suíte existente cobre nominalmente loaders, Registry, state, engine, runtime,
artifacts, gates, logging, CLI e um E2E. Lacunas relevantes antes desta QA:

- somente uma transição válida e uma inválida;
- nenhuma coerência global/etapa;
- nenhum teste multiprocesso;
- nenhum stale-write/version conflict;
- nenhum `awaiting_approval`/`cancelled` no CLI;
- nenhuma associação cruzada de artefato;
- nenhuma colisão de sidecar;
- nenhum workflow vazio;
- fault injection insuficiente para snapshot/audit/reconciliação.

## 6. Testes adicionais de QA

Foram adicionados 30 casos em `tests/qa/`, descritos em
[`sprint-2-qa-test-report.md`](sprint-2-qa-test-report.md).

A regressão total em raiz curta obteve:

```text
68 passed in 8.40s
TOTAL 1198 statements, 96 missing, 92% coverage
```

Passar esses testes não significa ausência de defeitos: vários casos afirmam e
registram comportamentos inseguros reproduzidos para evitar falso negativo.

## 7. Resultados por área

### 7.1 Máquinas de estado

**Aderências**

- todas as arestas declaradas em `EXECUTION_TRANSITIONS` e
  `STAGE_TRANSITIONS` aceitam apenas os alvos listados;
- estados `completed` e `cancelled` são terminais;
- histórico de transição sobrevive a save/load;
- `run_id` exige UUID v4.

**Falhas**

- não existe máquina separada de Project;
- `transition_execution(running, completed)` aceita etapa `pending`;
- `transition_stage()` não valida compatibilidade com o estado global;
- mutação ocorre antes do save; falha de persistência deixa memória e disco
  divergentes;
- `ExecutionState` não tem `version` nem `last_event_id`.

Resultado: **reprovado**.

### 7.2 Recuperação e retomada

**Aderências**

- `resume` de blocked preserva `run_id` e cria nova tentativa na suíte existente;
- etapa `completed` é ignorada por `next_stage()`;
- completed e cancelled são rejeitados;
- failed e blocked são estados admitidos por `prepare_resume()`.

**Falhas**

- `awaiting_approval` é rejeitado e não existe `asep approve/reject`;
- resume não revalida versões/fingerprint, inputs, evidências, gates e artefatos
  já persistidos conforme ADR-007;
- não existe detecção/reconciliação de interrupção entre artefato, gate, snapshot
  e log;
- tentativa anterior não é um registro imutável separado; só há contador;
- uma falha depois de persistir artefato pode tornar resume inviável por colisão.

Resultado: **reprovado**.

### 7.3 Integridade dos artefatos

**Aderências**

- `..` e path absoluto são rejeitados;
- arquivo e metadata carregam run/project/stage/agent;
- checksum SHA-256 é gravado;
- colisão do arquivo principal é rejeitada;
- temporários são removidos nas falhas cobertas.

**Falhas**

- estado aceita `artifact_reference` de outro run/projeto;
- não há API que revalide checksum ao carregar/retomar;
- sidecar de metadata preexistente é sobrescrito;
- arquivo e metadata não formam transação atômica;
- o manifest decidido no ADR-011 é representado por sidecars, sem validação
  cruzada posterior;
- colisão na retomada após artefato parcialmente persistido impede recuperação.

Resultado: **reprovado**.

### 7.4 Concorrência local

**Evidência**

- dois snapshots obsoletos salvaram com sucesso; a segunda gravação apagou a
  transição do primeiro;
- dois processos carregaram o mesmo run bloqueado e passaram por
  `prepare_resume`; um gravou e outro recebeu `StatePersistenceError` por disputa
  do mesmo `.tmp`;
- não há lockfile, mutex, version check, compare-and-swap ou limitação operacional
  aplicada pelo código;
- nomes temporários usam `run_id`, portanto são iguais entre processos do mesmo run.

**Classificação:** risco de corrupção/perda de atualização **BLOQUEADOR**. A
documentação de débito não mitiga nem impede o comportamento.

### 7.5 Workflow Engine

| Cenário | Resultado |
|---|---|
| dependência inexistente | rejeitada pelo loader/engine |
| ciclo | rejeitado |
| ordem topológica | respeitada |
| parallel | rejeitado com `CAPABILITY_NOT_SUPPORTED` |
| conditional | rejeitado com `CAPABILITY_NOT_SUPPORTED` |
| tailoring sequencial | explícito e registrado |
| etapa bloqueada | não avança; retorna a etapa em retomada |
| workflow vazio | **aceito indevidamente** |
| dependência não concluída | `next_stage()` retorna `None`; run pode ficar `running` sem diagnóstico |

Resultado: **parcial/reprovado**.

### 7.6 Agent Runtime e Quality Gates

**Aderências**

- agente sem adaptador, contrato ausente, resultado com identidade divergente e
  exceção são tratados por erros tipados;
- exceção do agente não expõe a mensagem original;
- decisões `APPROVED`, `APPROVED_WITH_PENDING` e `BLOCKED` são exercitadas;
- gate bloqueado impede completar a etapa.

**Falhas**

- `QualityGateEngine` não carrega `GateDefinition` declarativa nem registra
  evaluator/owner, evidence refs, findings ou exceções;
- `GateResult` é mutável e não identifica tentativa;
- `APPROVED_WITH_PENDING` completa a etapa sem registrar owner, validade ou plano;
- `AgentRuntime` verifica a presença da referência de contrato, mas depende do
  loader anterior para validar seu conteúdo;
- resultado `FAILED` do agente é transformado em `blocked`, não em estado
  `failed`, perdendo semântica.

Resultado: **parcial/reprovado**.

### 7.7 CLI e fluxo ponta a ponta

Execução real:

```text
Run ID: b8732fb4-cba8-4a90-a99d-3c05cf013658
Estado: completed
Etapa: business_analysis
Etapas concluídas: 1
Exit code: 0
```

Retomada desse run:

```text
RUN_NOT_RESUMABLE Execução em estado não retomável: completed
Exit code: 6
```

Falhas:

- run bloqueado retorna código `0`, indistinguível de sucesso para automação;
- não há comandos approve, reject ou cancel;
- saída e logs não deixam explícito que o tailoring cobre somente BA e não o
  lifecycle;
- caminho longo do Windows quebra três testes E2E;
- o primeiro log é aberto antes de validar projeto/Registry, podendo deixar log
  órfão para execução jamais criada.

Resultado: **parcial/reprovado**.

## 8. Aderência detalhada ao ADR-014

| Decisão/consequência/risco | Evidência | Situação |
|---|---|---|
| tailoring `asep-self-development-sequential` 0.1.0 | arquivo e Registry coincidem | aderente |
| uma etapa Business Analysis | `stages: [business_analysis]` | aderente |
| um único agente | `business-analyst` | aderente |
| gate `QG-ANALYSIS` | workflow, Registry e artefato real | aderente |
| projeto piloto usa tailoring | `project.yaml.workflow_id` e run real | aderente |
| workflow corporativo inalterado | arquivo separado continua com parallel/conditional | aderente |
| engine rejeita parallel | teste existente e validação do código | aderente |
| engine rejeita conditional | teste existente e validação do código | aderente |
| não fingir suporte aos demais agentes | runtime só registra adapter BA | aderente |
| nova etapa exige nova versão/aprovação | nenhum mecanismo runtime impede edição mantendo versão | **não garantido** |
| tailoring não representa lifecycle completo | ADR diz; CLI/log não dizem | **desvio parcial** |
| CLI deve explicitar limitação | mostra “execução sequencial”, não “BA-only/piloto” | **desvio** |
| relatórios devem explicitar limitação | relatórios de implementação/teste informam | aderente |
| logs devem explicitar limitação | nenhum evento/campo registra tailoring limitado | **desvio** |
| testes de rejeição preservam fail-closed | parametrização parallel/conditional existe | aderente |

Conclusão do ADR-014: **aderência funcional principal, com desvios de
observabilidade e enforcement de versionamento/aprovação**. A aderência ao
ADR-014 isoladamente não compensa violações dos ADR-003/006/007/008/009/010/011.

## 9. Defeitos encontrados

| ID | Severidade | Defeito | Evidência reproduzível |
|---|---|---|---|
| S2-QA-001 | bloqueador | ausência de lock/version conflict causa lost update | QA-S2-T10/T11 |
| S2-QA-002 | bloqueador | estado global pode concluir com etapa pendente | QA-S2-T03 |
| S2-QA-003 | bloqueador | referência de artefato de outro run/projeto é aceita | QA-S2-T07 |
| S2-QA-004 | bloqueador | crash não tem intent/outcome/reconciliação/audit | QA-S2-T05 + inspeção |
| S2-QA-005 | alto | awaiting_approval não possui decisão/retomada | QA-S2-T06 + CLI |
| S2-QA-006 | alto | sidecar de metadata é sobrescrito | QA-S2-T08 |
| S2-QA-007 | alto | checksum é apenas gravado, não validado | QA-S2-T09 |
| S2-QA-008 | alto | caminho longo quebra run/resume E2E no Windows | 3 falhas existentes |
| S2-QA-009 | alto | artifact + metadata + state não são transação recuperável | fault injection/inspeção |
| S2-QA-010 | médio | workflow vazio é aceito e pode concluir sem gate | QA-S2-T12 |
| S2-QA-011 | médio | blocked no CLI retorna código 0 | E2E existente/CLI |
| S2-QA-012 | alto | Gate Engine diverge do modelo estruturado ADR-008 | inspeção de modelos/engine |
| S2-QA-013 | alto | log diagnóstico e audit trail não são separados | arquivos/código/DT-002 |
| S2-QA-014 | médio | limitação BA-only não aparece no CLI/log | run e JSONL reais |
| S2-QA-015 | médio | baseline sem commit verificável | ausência de `.git` |

## 10. Severidade e evidência

Critério usado:

- **bloqueador:** pode corromper estado/evidência, concluir falsamente ou quebrar
  isolamento entre runs;
- **alto:** viola decisão aceita e compromete recovery, gate ou operação crítica;
- **médio:** comportamento incorreto contornável sem corrupção imediata;
- **baixo:** impacto localizado sem afetar decisão de gate.

Não foram classificados como baixo riscos de integridade conhecidos. Os testes,
estado real, logs, artefatos e caminhos dos casos estão descritos no relatório de
testes.

## 11. Riscos de concorrência

| Risco | Probabilidade local | Impacto | Classificação |
|---|---|---|---|
| dois resumes do mesmo run | plausível por operador/automação | erro parcial e disputa de tmp | bloqueador |
| stale write | plausível sem version check | perda silenciosa de histórico | bloqueador |
| tmp igual por run | certa sob disputa do mesmo artefato/state | falha/nondeterminismo | alto |
| dois runs distintos | diretórios segregados por UUID | baixo risco de colisão principal | baixo |
| log append concorrente do mesmo run | sem lock/schema de audit | interleaving/truncamento possível | alto |

Limitação documentada não é controle equivalente: o CLI não impede a segunda
instância e não informa “run locked”.

## 12. Riscos de corrupção e recuperação

- snapshot atômico isolado reduz YAML parcial, mas não resolve consistência entre
  snapshot, artefato, metadata, gate e log;
- crash após artefato e antes do snapshot deixa arquivo órfão; resume colide;
- crash após snapshot e antes do log deixa audit incompleto;
- crash após conteúdo e antes do sidecar remove o conteúdo no tratamento de
  erro, mas não reconcilia referência já mantida em memória;
- linha JSONL truncada não é detectada;
- checksum adulterado não é verificado;
- não existe `last_event_id`, marker, replay ou rotina de repair;
- erro durante save não desfaz transição no objeto.

**Classificação geral de corrupção/recuperação: bloqueador.**

## 13. Débitos técnicos

Débitos já reconhecidos e ainda abertos:

- DT-001: estrutura não adere integralmente ao ADR-002;
- DT-002: audit trail não separado;
- DT-004: análise estática ausente;
- DT-005: política de cobertura provisória;
- DT-006: lock single-writer ausente;
- DT-007: aprovação humana ausente;
- DT-008: somente BA executável, por desenho;
- DT-009: Security Review pendente.

Novos débitos/defeitos a registrar: coerência global/etapa, validação cruzada de
artefatos, colisão de sidecar, verificação de checksum, path length, workflow
vazio e semântica de exit code.

## 14. Pendências humanas

| Pendência | Autoridade | Condição |
|---|---|---|
| definir fluxo approve/reject e identidade declarativa | Product Owner + Governance | ADR-009 operacionalizado |
| aprovar política/ferramenta de cobertura | Quality Lead | decisão registrada |
| decidir tratamento arquitetural de recovery transacional | Software Architect | ADR/alteração aprovada |
| aceitar ou corrigir risco de caminho longo suportado | Product + Engineering | matriz de SO declarada |
| realizar Security Review | Security Engineer | relatório e gate |
| fornecer baseline identificável | responsável pelo repositório | SHA/worktree |

QA não aceita risco alto fora de sua autoridade.

## 15. Classificação final

**`BLOCKED`**

Justificativa objetiva: existem defeitos reproduzíveis de perda de atualização,
ausência de exclusão de escritor, falsa coerência de estado e associação cruzada
de artefatos. Esses defeitos violam critérios nucleares e ADRs aceitos. Portanto,
`APPROVED_WITH_PENDING` não é aplicável.

## 16. Condições necessárias para aprovação

1. implementar lock single-writer cross-process para run/state/artifacts/logs,
   com teste de dois resumes e timeout/erro explícito;
2. adicionar version/compare-and-swap e impedir stale write;
3. implementar `last_event_id`, intent/outcome ou mecanismo equivalente,
   detecção de log truncado e reconciliação testada;
4. validar invariantes globais/etapas antes de save e conclusão;
5. tipar `artifact_references` e exigir igualdade de run/project/stage, existência,
   metadata e checksum;
6. tornar persistência de artefato/metadata recuperável e tratar colisões de ambos;
7. implementar ou retirar formalmente do escopo aceito o fluxo
   approve/reject/resume de `awaiting_approval`;
8. alinhar Gate Engine ao ADR-008, com definição, tentativa, owner, evidências,
   findings e pendências rastreáveis;
9. rejeitar workflow vazio e diagnosticar deadlock/dependência não satisfeita;
10. definir e testar suporte a paths longos no Windows;
11. separar audit trail de log diagnóstico conforme ADR-010;
12. expor a limitação BA-only no CLI e nos logs;
13. entregar commit identificável e repetir suíte existente + QA adicional;
14. obter Security Review e aceite humano de qualquer risco residual alto.

## Handoff obrigatório

**Contexto:** Sprint 2 revisada independentemente, sem correção de produção.  
**Objetivo atingido:** classificação baseada em evidência reproduzível.  
**Entradas:** repositório, contratos, workflows, testes, relatórios e ADRs.  
**Validações:** suíte existente, QA adicional, fault injection, concorrência e
CLI real.  
**Artefatos:** este relatório, relatório de testes e `tests/qa/`.  
**Fatos:** 68 testes passam em raiz curta; 3 E2E falham em raiz longa; defeitos
S2-QA-001 a 015 registrados.  
**Hipótese:** o risco multiprocesso pode variar com escalonamento; a ausência de
lock e o lost update já são fatos, portanto a hipótese não muda a classificação.  
**Decisão de QA:** gate bloqueado.  
**Riscos:** corrupção, perda de auditabilidade, isolamento cruzado e recovery
ambíguo.  
**Pendências:** itens da seção 14.  
**Checklist:** todos os oito focos obrigatórios exercitados; código de produção
inalterado; Sprint 3 não iniciada.  
**Próxima ação:** Engineering corrige; Architect revisa aderência; QA revalida.  
**Responsável:** Engineering + Software Architect; Quality Lead agenda reteste.  
**Prazo/gatilho:** nova revisão somente após todas as condições 1–13 com evidência;
item 14 antes de liberação.
