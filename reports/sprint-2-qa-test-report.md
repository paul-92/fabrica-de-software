# Relatório de Testes Independentes de QA — Sprint 2

**Projeto:** ASEP Self-development  
**Público:** Product Owner, Quality Lead, Software Architect e Engineering  
**Dono:** QA independente da Sprint 2  
**Versão:** 1.0.0  
**Status:** concluído — evidência para gate bloqueado  
**Data:** 2026-07-29

## 1. Contexto e objetivo

Este relatório registra testes adicionais, independentes da implementação, para
estado, retomada, artefatos, concorrência, workflow, runtime, gates e CLI. Nenhum
código de produção foi alterado. Os artefatos de QA adicionados são:

- `tests/qa/test_sprint_2_independent_qa.py`;
- `tests/qa/concurrent_resume_probe.py`.

## 2. Ambiente e versão

| Item | Valor |
|---|---|
| Sistema | Microsoft Windows, build `10.0.26200.8655`, 64 bits |
| Python efetivo | `3.14.4` em `.venv` |
| pytest | `8.4.2` |
| Pydantic | `2.13.4` |
| Typer | `0.27.0` |
| PyYAML | `6.0.3` |
| Rich | `14.3.4` |
| Jinja2 | `3.1.6` |
| Commit | indisponível: a cópia avaliada não contém `.git/` e `git` não está no PATH |

O relatório do desenvolvedor informa o mesmo Python principal, mas versões de
dependências não estavam registradas nele. A ausência do commit impede afirmar
rastreabilidade criptográfica da baseline.

## 3. Comandos e resultados reproduzíveis

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest --basetemp C:\qa-asep\existing
.\.venv\Scripts\python.exe -m pytest --basetemp <raiz-longa-no-workspace>
.\.venv\Scripts\python.exe -m pytest tests\qa --basetemp C:\qa-asep\independent -q
.\.venv\Scripts\python.exe -m pytest --basetemp C:\qa-asep\all --cov=asep --cov-report=term-missing
.\.venv\Scripts\asep.exe run projects\asep-self-development
.\.venv\Scripts\asep.exe resume b8732fb4-cba8-4a90-a99d-3c05cf013658
```

Resultados:

| Execução | Resultado |
|---|---|
| dependências | nenhum conflito |
| suíte existente, raiz curta | `38 passed in 5.14s` |
| suíte existente, raiz longa | `35 passed, 3 failed in 4.99s` |
| QA adicional isolado | `30 passed` |
| regressão existente + QA | `68 passed in 8.40s`; cobertura total `92%` |
| CLI `run` real | código `0`; run `b8732fb4-cba8-4a90-a99d-3c05cf013658`; `completed` |
| CLI `resume` de completed | código `6`; `RUN_NOT_RESUMABLE` |
| validação documental | não concluída: diretórios temporários inacessíveis ao validador |

Os três testes que falham em raiz longa são:

- `test_cli_run_prepares_project`;
- `test_cli_end_to_end_persists_state_artifact_gate_and_log`;
- `test_cli_resume_keeps_run_id_and_does_not_repeat_completed_stage`.

Todos falham com `ARTIFACT_ERROR`, código `5`, ao criar o arquivo temporário do
artefato em caminho longo no Windows.

## 4. Matriz dos testes adicionais

| ID | Área | Cenário | Resultado observado |
|---|---|---|---|
| QA-S2-T01 | estado | matriz completa de transições globais | alvos declarados aceitos; demais rejeitados |
| QA-S2-T02 | estado | matriz completa de transições de etapa | alvos declarados aceitos; demais rejeitados |
| QA-S2-T03 | coerência | global `completed` com etapa `pending` | combinação inválida aceita |
| QA-S2-T04 | histórico | salvar e recarregar transição | histórico preservado |
| QA-S2-T05 | fault injection | falha em `os.replace` do snapshot | disco fica antigo; objeto em memória fica avançado |
| QA-S2-T06 | resume | `awaiting_approval`, `completed`, `cancelled` | todos rejeitados |
| QA-S2-T07 | artefatos | referência com outro run/projeto | aceita e persiste |
| QA-S2-T08 | artefatos | sidecar preexistente | sobrescrito sem colisão |
| QA-S2-T09 | artefatos | adulteração após persistência | checksum não é revalidado |
| QA-S2-T10 | concorrência | dois snapshots obsoletos gravam | atualização do primeiro é perdida |
| QA-S2-T11 | concorrência | dois processos retomam mesmo run | um grava; outro falha em persistência; nenhum lock preventivo |
| QA-S2-T12 | workflow | workflow vazio | aceito e ordenado como vazio |
| QA-S2-T13 | runtime | exceção do agente | convertida em `AgentExecutionError`, sem vazar detalhe |

As parametrizações das duas máquinas de estado geram 17 casos; o conjunto
adicional totaliza 30 testes coletados.

## 5. Evidências principais

### QA-S2-001 — incoerência de estado

`StateManager.transition_execution()` valida somente a aresta global. Ele aceita
`running -> completed` sem confirmar que todas as etapas estão `completed`.

### QA-S2-002 — falha durante gravação

Com fault injection no replace atômico, o snapshot anterior permanece íntegro,
mas o objeto em memória já contém estado e histórico novos. Não existe rollback,
intent/outcome, marker ou reconciliação para decidir qual visão é autoritativa.

### QA-S2-003 — associação cruzada

`ExecutionState.artifact_references` é `list[dict]`. Um item com outro `run_id`,
outro projeto, etapa e agente passou por `save()` e `load()` sem erro.

### QA-S2-004 — colisão de metadados

O manager verifica apenas a existência do artefato principal. Um
`summary.md.metadata.yaml` preexistente foi substituído silenciosamente.

### QA-S2-005 — perda de atualização

Dois escritores carregaram o mesmo snapshot. Ambos avançaram para `ready` com
motivos diferentes. Após duas gravações válidas, somente o histórico do segundo
permaneceu.

### QA-S2-006 — workflow vazio

O modelo e o engine aceitaram zero etapas, zero agentes e zero gates. O resultado
ordenado foi vazio, permitindo conclusão sem trabalho ou gate.

### QA-S2-007 — disputa multiprocesso

Dois processos carregaram o mesmo run bloqueado antes do sinal de início. Ambos
passaram pela preparação da retomada. Resultado observado:

```text
competing_resume_outcomes=[
  ('error', 'StatePersistenceError'),
  ('saved', None)
]
```

A falha decorre do arquivo temporário compartilhado, não de controle
single-writer. O comportamento pode variar por escalonamento e não oferece
exclusão, version check ou mensagem de conflito de lock.

## 6. Cobertura dos focos obrigatórios

| Foco | Cobertura | Lacuna residual |
|---|---|---|
| máquinas de estado | matrizes completas, inválidas, histórico, fault injection, coerência | não há máquina Project separada |
| recuperação | blocked, failed por suíte existente; completed/cancelled/awaiting por QA | não existe fluxo de aprovação/cancelamento CLI |
| artefatos | traversal existente; metadata, checksum, colisão e associação cruzada por QA | não existe API de leitura/verificação |
| concorrência | stale writers e dois processos | stress prolongado não é necessário para provar ausência de lock |
| ADR-014 | tailoring real, CLI real, modos rejeitados | limitação não aparece claramente na saída CLI/log |
| workflow | ciclo, dependência inexistente, modos, ordem e vazio | condicionais são somente rejeitadas |
| runtime/gates | agente/contrato/resultado/exceção; três decisões | gate não usa definição declarativa do Registry |
| CLI/E2E | run real, resume blocked existente, completed real | awaiting/cancelled não possuem comando público para criação/decisão |

## 7. Riscos residuais e conclusão

Os testes comprovam risco de perda de histórico/atualização concorrente e
associação cruzada de artefatos. Esses resultados invalidam garantias centrais
dos ADR-003, ADR-006, ADR-007 e ADR-011.

**Resultado do conjunto de QA:** tecnicamente executável no caminho feliz e
determinístico, porém insuficiente para aprovação da Sprint 2. Evidência
encaminhada para classificação `BLOCKED`.

## 8. Checklist e handoff

- [x] suíte existente executada antes dos testes adicionais;
- [x] testes adicionais separados do código de produção;
- [x] falhas e ambiente registrados;
- [x] concorrência multiprocesso exercitada;
- [x] CLI real exercitado;
- [x] cobertura consolidada registrada;
- [ ] commit da baseline confirmado — indisponível nesta cópia;
- [ ] riscos altos aceitos — não autorizado ao QA.

**Próxima ação:** Engineering corrige os bloqueadores; Software Architect valida
aderência aos ADRs; QA independente repete toda a matriz sobre commit
identificável.  
**Responsáveis:** Engineering e Software Architect; reentrada do QA após entrega
de commit, relatório de correções e evidências.  
**Gatilho:** todos os bloqueadores do relatório principal encerrados.
