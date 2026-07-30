# ASEP Release Candidate RC1

**Dono:** Engenharia ASEP | **Versão candidata:** 0.1.0-rc1  
**Status:** tecnicamente validado; publicação bloqueada por Git/CI  
**Data:** 2026-07-30

## Visão geral

O RC1 consolida Observabilidade, Persistência e Orquestração. Não adiciona
funcionalidade à Sprint 8.6; registra auditoria, correções de reprodutibilidade e
gates antes da Fase 9.

## Arquitetura

```text
CLI/API
  -> application/orchestrators
      -> WorkflowEngine -> WorkflowStep
      -> AgentRegistry -> AgentStepAdapter
      -> WorkflowPersistenceService
  -> repository ports -> memory/file/sqlite
  -> RunQueryService -> Metrics/Dashboard
```

Módulos existentes incluem execution, workflow, agents, providers, prompting,
execution package, artifacts, quality gates, repositories, configuration,
SQLite, Timeline, Metrics, Dashboard API, ExecutionGraph e exporters.

## Estatísticas reproduzíveis

| Métrica | Valor |
|---|---:|
| módulos Python em `src/asep` | 116 |
| classes | 250 |
| Protocols explícitos | 10 |
| funções e métodos | 438 |
| testes coletados/aprovados | 665 |
| cobertura | 95% |
| módulos de teste `test_*.py` | 41 |
| ADRs documentados | 8 |
| documentos de Sprint | 7 |
| documentos Markdown em `docs/` | 61 |
| documentos de Fase | 2 |
| Fases declaradas concluídas | 3 |
| ciclos internos de import | 0 |

Contagens foram geradas com biblioteca padrão/PowerShell e podem mudar após
versionar estes próprios documentos.

## Estado

- Fases 6, 7 e 8 concluídas localmente;
- Sprint 8.6 é hardening/RC1;
- Python suportado `>=3.12`, validado em 3.14.4/Windows 11;
- 665 testes verdes;
- `compileall`, links, `pip check` e `git diff --check` aprovados;
- nenhuma funcionalidade nova na Sprint 8.6.

## Limitações

- workflow síncrono e sequencial;
- sem retomada automática de WorkflowSnapshot;
- Agent Registry somente em memória;
- sem lockfile;
- sem migrations versionadas;
- Dashboard não expõe WorkflowSnapshots;
- cobertura inferior a 80% em alguns ramos de infraestrutura;
- validação completa apenas no Windows desta máquina.

## Riscos

O maior risco é operacional: o trabalho acumulado está não commitado e o remoto
está atrás. Também permanecem riscos médios de metadata sensível, ausência de
scanner de histórico e resolução variável de dependências.

## Critérios antes da Fase 9

- [ ] revisão humana do diff acumulado;
- [ ] commits e push autorizados;
- [ ] CI ou clone limpo com todos os gates;
- [ ] scanner de segredos no histórico;
- [ ] decisão sobre lockfile;
- [ ] backup/restauração testados quando houver dados relevantes;
- [ ] aprovação formal do escopo da Fase 9;
- [ ] tag RC criada somente por pessoa autorizada.

## Roadmap

A Fase 9 não foi iniciada. Novos agentes, paralelismo, filas, eventos, plugins e
retomada continuam fora do RC1.

## Evidências

[Architecture Audit](../audits/ArchitectureAudit.md),
[Code Audit](../audits/CodeAudit.md),
[Test Audit](../audits/TestAudit.md),
[Dependency Audit](../audits/DependencyAudit.md),
[Security Audit](../audits/SecurityAudit.md),
[Git Audit](../audits/GitAudit.md) e
[Migration Guide](../migration/MigrationGuide.md).
