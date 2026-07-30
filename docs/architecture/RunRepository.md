# Run Repository

**Dono:** Engenharia ASEP | **Versão:** 1.1 | **Status:** persistência em arquivo disponível

## Objetivo

O pacote `asep.runs` define uma representação neutra de uma execução e a porta
mínima para armazená-la. Nesta versão há somente uma implementação em memória;
nenhum dado sobrevive ao encerramento do processo.

```mermaid
flowchart LR
    RUN["Run + RunStatus + RunError"] --> PORT["RunRepository Protocol"]
    PORT --> MEMORY["InMemoryRunRepository"]
    PORT --> FILE["FileRunRepository"]
    FILE --> JSON["runs.json"]
    LOCATOR["RunLocator"] -. localiza state.yaml .-> STATE["ExecutionState em disco"]
```

## Modelo Run

| Campo | Semântica |
|---|---|
| `id` | identidade única e não vazia |
| `status` | estado resumido do run |
| `started_at` | início com timezone |
| `finished_at` | término opcional, nunca anterior ao início |
| `project_id` | projeto opcional |
| `workflow_id` | workflow opcional |
| `stage_id` | etapa atual ou relacionada, opcional |
| `provider_name` | provider opcional, como texto neutro |
| `summary` | resumo opcional |
| `error` | `RunError` serializável, nunca exceção Python |
| `metadata` | árvore JSON imutável |

`Run` e `RunError` são modelos Pydantic estritos e frozen. Metadata aceita
somente null, strings, números finitos, booleanos, listas e objetos com chaves
string. Objetos arbitrários, classes, sets, exceptions, callbacks e conexões
externas são rejeitados.

## RunStatus

- não terminais: `pending`, `running`;
- terminais: `succeeded`, `failed`, `cancelled`.

`is_terminal` expõe essa classificação. Não há máquina de estados ou validação
de transição nesta sprint.

## Contrato

```python
class RunRepository(Protocol):
    def save(self, run: Run) -> None: ...
    def get(self, run_id: str) -> Run: ...
    def list(self) -> tuple[Run, ...]: ...
```

- `save` insere ou substitui explicitamente o snapshot com o mesmo ID;
- `get` devolve uma cópia profunda ou lança o `RunNotFoundError` existente;
- `list` devolve cópias em tupla, ordenadas por `started_at` e `id`;
- nenhuma operação expõe a coleção interna.

## Implementação em memória

Cada `InMemoryRunRepository` possui seu próprio dicionário. O repositório
normaliza cada entrada por round-trip serializável e faz o mesmo ao devolver
resultados. Ele é apropriado para testes e composição local, não para auditoria,
concorrência, múltiplos processos ou recuperação.

## Implementação em arquivo

`FileRunRepository(path)` implementa o mesmo Protocol em um único arquivo JSON.
O construtor carrega o snapshot existente; se o arquivo não existir, cria o
diretório pai e um documento vazio usando escrita atômica. Arquivo existente de
zero bytes representa coleção vazia e será normalizado na próxima gravação.

O envelope persistente é:

```json
{
  "runs": [
    {
      "error": null,
      "finished_at": null,
      "id": "run-id",
      "metadata": {},
      "project_id": "project",
      "provider_name": null,
      "stage_id": null,
      "started_at": "2026-07-30T10:00:00Z",
      "status": "pending",
      "summary": null,
      "workflow_id": "workflow"
    }
  ],
  "version": "1.0"
}
```

`RunCodec` enumera explicitamente todos os campos do modelo. Status usa seu
valor estável, timestamps usam ISO 8601 com timezone, e `RunError`, metadata e
Unicode são preservados. A desserialização passa novamente pela validação
estrita de `Run`.

`save` insere ou substitui o mesmo ID, escreve os Runs ordenados por
`started_at` e ID, e só atualiza o snapshot interno após a persistência
bem-sucedida. `get` e `list` devolvem cópias profundas.

### Atomicidade e erros

A gravação cria temporário curto no mesmo diretório, executa flush e `fsync`,
fecha o arquivo e chama `os.replace`. Falhas removem o temporário quando
possível, preservam o arquivo e o snapshot anteriores e geram
`RunStorageWriteError`.

JSON malformado, envelope ou versão divergente, registros inválidos e IDs
duplicados geram `InvalidRunStorageFormatError`. Falhas do filesystem são
encadeadas em `RunStorageReadError` ou `RunStorageWriteError`, sem incluir o
conteúdo do arquivo na mensagem.

### Limitações

- cada instância mantém o snapshot carregado no construtor;
- mudanças externas exigem nova instância para serem observadas;
- não há lock nem coordenação multiprocesso, portanto escritores concorrentes
  podem causar lost update;
- o documento inteiro é reescrito e não é adequado para alto volume;
- a composição padrão usa memória por meio da `RepositoryFactory`;
- o backend em arquivo e os nomes finais podem ser selecionados por
  `ApplicationSettings`;
- `Configuration.load()` aceita defaults e variáveis de ambiente `ASEP_*`.

## Implementação SQLite

`SQLiteRunRepository(path)` implementa o mesmo Protocol e faz upsert por
`Run.id`. O schema é criado automaticamente e o payload usa `RunCodec`, mantendo
todos os campos, metadata e timestamps com timezone. Novas instâncias apontadas
ao mesmo banco observam os Runs persistidos.

Exemplo:

```python
repository = FileRunRepository(Path("storage/runs.json"))
repository.save(run)
restored = FileRunRepository(Path("storage/runs.json")).get(run.id)
```

## RunLocator

`RunLocator` e `RunRepository` coexistem:

- `RunLocator` procura exatamente um
  `projects/*/.asep/runs/<uuid>/state.yaml` no filesystem;
- `RunRepository` armazena e consulta snapshots `Run` por contrato;
- o locator não mantém índice, não devolve `Run` e não substitui repository;
- o repository em memória não conhece paths nem substitui a persistência de
  `ExecutionState`.

Uma composição durável futura poderá usar os paths existentes, mas ainda exige
decisão sobre reconciliação com `StateManager`.

## Integração futura

Não houve integração com Orchestrator nesta sprint. Antes disso é necessário
decidir:

- mapeamento entre `ExecutionStatus` e `RunStatus`;
- momento de criação e atualização;
- comportamento em resume;
- fonte de `summary`, `error` e provider;
- atomicidade entre `ExecutionState` e um repository durável.

A Sprint 6.2 implementou o domínio e armazenamento em memória da
[Execution Timeline](ExecutionTimeline.md), associados ao `Run.id`. A
instrumentação do fluxo e toda persistência durável permanecem pendentes.
