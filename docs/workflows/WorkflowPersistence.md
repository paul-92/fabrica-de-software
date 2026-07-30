# Workflow Persistence

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Responsabilidades

Separar objetos vivos do workflow de sua representação persistida e oferecer
consultas independentes do backend.

## Fluxo

```text
Definition + ExecutionResult
             |
             v
WorkflowPersistenceService
             |
             v
WorkflowSnapshot -> RepositoryFactory -> memory/file/sqlite
```

## Contrato do repository

```python
save(snapshot)
update(snapshot)
get(snapshot_id)
exists(snapshot_id)
list()
find_by_status(status)
find_by_run(run_id)
find_by_workflow(workflow_id)
find_by_period(started_at, finished_at)
```

Ausência e duplicidade são erros explícitos. Não foi adicionado `delete`,
porque snapshots representam histórico auditável e não existe caso de uso de
remoção aprovado.

## Serialização e segurança

O codec usa apenas JSON. Metadados e métricas passam pela validação
`freeze_json`; objetos Python arbitrários e credenciais não são necessários.
Timeline é referenciada por IDs, evitando duplicar eventos.

O backend file usa envelope versionado e substituição atômica no mesmo
filesystem. SQLite reutiliza `SQLiteDatabase`, conexões transacionais e schema
validado.

## Queries

Todas as implementações retornam tuplas ordenadas por início e ID. O período
compara `started_at` de forma inclusiva. Busca inexistente retorna coleção vazia;
`get` obrigatório lança exceção.

## Integração

`WorkflowOrchestrator` depende de uma pequena porta estrutural e chama
`persist(workflow, result)`. O `WorkflowEngine` continua limitado a validar e
executar; não importa Factory, repositories ou SQLite.

## Limitações

Snapshots são leitura histórica, não checkpoints retomáveis. Não há migration
versionada, API de Dashboard, retenção ou concorrência distribuída.

## Referências

[Sprint 8.5](../phase-08/Sprint-8.5-Workflow-Persistence.md),
[ADR-021](../adr/ADR-021-workflow-snapshot-persistence.md) e
[Database Schema](../persistence/DatabaseSchema.md).

