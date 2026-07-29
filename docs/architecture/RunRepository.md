# Run Repository

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

## Objetivo

O pacote `asep.runs` define uma representação neutra de uma execução e a porta
mínima para armazená-la. Nesta versão há somente uma implementação em memória;
nenhum dado sobrevive ao encerramento do processo.

```mermaid
flowchart LR
    RUN["Run + RunStatus + RunError"] --> PORT["RunRepository Protocol"]
    PORT --> MEMORY["InMemoryRunRepository"]
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

## RunLocator

`RunLocator` e `RunRepository` coexistem:

- `RunLocator` procura exatamente um
  `projects/*/.asep/runs/<uuid>/state.yaml` no filesystem;
- `RunRepository` armazena e consulta snapshots `Run` por contrato;
- o locator não mantém índice, não devolve `Run` e não substitui repository;
- o repository em memória não conhece paths nem substitui a persistência de
  `ExecutionState`.

Uma implementação durável futura poderá usar os paths existentes, mas isso
exige decisão sobre reconciliação com `StateManager`.

## Integração futura

Não houve integração com Orchestrator nesta sprint. Antes disso é necessário
decidir:

- mapeamento entre `ExecutionStatus` e `RunStatus`;
- momento de criação e atualização;
- comportamento em resume;
- fonte de `summary`, `error` e provider;
- atomicidade entre `ExecutionState` e um repository durável.

A Sprint 6.2 poderá associar eventos de Timeline ao `Run.id`, mas Timeline,
eventos e persistência durável não fazem parte desta implementação.
