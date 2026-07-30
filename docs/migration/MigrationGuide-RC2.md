# Guia de migração para o RC2

**Público:** mantenedores e operadores da ASEP  
**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** vigente para validação do RC2  
**Data:** 2026-07-30

## Objetivo

Orientar a atualização do RC1 para o RC2 sem presumir que as mudanças locais já
foram publicadas. Este guia não autoriza commit, push, tag ou release.

## Pré-requisitos

- Python 3.12 ou superior;
- Git e ambiente virtual local;
- cópia integral do worktree quando houver mudanças não versionadas;
- revisão de dados locais ignorados (`storage`, bancos, logs e artefatos);
- autoridade explícita antes de publicar ou criar tag.

## Atualização

1. Preserve o repositório e os dados locais.
2. Confirme branch, commit e `git status --short`.
3. Instale o projeto em ambiente virtual:

   ```text
   python -m pip install -e ".[test]"
   ```

4. Valide dependências:

   ```text
   python -m pip check
   ```

5. Execute os gates:

   ```text
   python -m pytest -v
   python -m compileall src tests examples
   git diff --check
   ```

6. Execute `examples/basic_analysis.py`, `directory_summary.py` e
   `architecture_overview.py`.
7. Faça revisão humana do diff antes de qualquer versionamento.

No Windows, se `%TEMP%` ou o sandbox tiver ACL incompatível, use um
`--basetemp` curto dentro do workspace. O diretório precisa ser gravável e não
deve ser versionado.

## Mudanças arquiteturais desde o RC1

```text
Goal -> ASEPEngine -> ExecutionPipeline
                        |
             Workflow -> Planning -> Coordination
                                      |
                               Supervisor -> Runtime
                                              |
                                      Agent -> Tool Registry -> Tools
                        |
                 Memory + Timeline + Metrics + Persistence
```

Novos limites:

- `planning` descreve e valida trabalho, sem executá-lo;
- `agents.coordination` resolve capabilities e delega ao Runtime;
- `runtime.recovery` supervisiona falhas por composição;
- `tools` medeia capacidades externas com isolamento de workspace;
- `memory` fornece persistência operacional e contexto;
- `pipeline` é a composition root/fachada, não um novo domínio.

## Nova API aditiva

```python
import asep

result = asep.execute("Liste a estrutura", workspace=".")
```

O uso anterior de CLI, Dashboard API, `WorkflowOrchestrator`, Orchestrator de
projeto, repositories e exporters continua válido. Não há remoção ou renomeação
intencional de API no RC2.

## Configuração e dados

O pipeline padrão usa repositories em memória e Tools somente de leitura. Ele
não migra automaticamente dados dos backends file/SQLite e não persiste
`GoalResult` entre processos. Continue usando o Configuration System e a
RepositoryFactory para os fluxos persistentes existentes.

Nenhuma migration de banco foi adicionada pelo RC2. Faça backup dos bancos
antes de trocar ambiente e preserve timezone/encoding.

## Segurança

- não copie `.env`, tokens ou bancos para Git;
- revise metadata antes de persistir;
- trate `MemoryFilter` como redução de risco, não garantia;
- mantenha o workspace mínimo necessário às Tools;
- execute scanner de segredos no histórico antes da publicação.

## Compatibilidade

| Área | RC1 | RC2 |
|---|---|---|
| Python | `>=3.12` | sem alteração |
| repositories | memory/file/sqlite | sem alteração |
| workflow | síncrono/sequencial | sem alteração |
| agentes | contratos/Registry | Runtime + coordenação |
| capacidades | internas ao agente | Tool Registry |
| resiliência | falha tipada | Supervisor/recovery |
| entrada E2E | composição manual | `asep.execute` |

## Rollback

Não há migration destrutiva de schema. Para retornar ao RC1, use uma referência
Git revisada e restaure dados a partir de backup. Não aplique `git reset
--hard` em worktree com alterações locais.

## Checklist de aceite operacional

- [ ] diff acumulado revisado;
- [ ] temporários rastreados tratados conscientemente;
- [ ] suite e exemplos aprovados em clone limpo;
- [ ] CI Windows e POSIX aprovado;
- [ ] histórico Git escaneado;
- [ ] política de lockfile decidida;
- [ ] backup/restauração verificados quando aplicável;
- [ ] commit, push e tag autorizados.

## Referências

[Release Candidate 2](../releases/ReleaseCandidate2.md),
[Sprint 9.8](../phase-09/Sprint-9.8-Platform-Hardening-RC2.md),
[Architecture Map](../architecture/ArchitectureMap.md),
[Project State](../../project/PROJECT_STATE.md) e
[Migration Checklist](../../project/MIGRATION_CHECKLIST.md).
