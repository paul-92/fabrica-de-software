# Repositórios SQLite da ASEP

**Público:** pessoas desenvolvedoras iniciantes e experientes  
**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** vigente desde a Sprint 7.5

## O que é?

Um repository, ou repositório, é uma porta usada pela aplicação para guardar e
recuperar informações. Pense nele como uma gaveta: quem pede para guardar um
objeto não precisa saber se a gaveta é de madeira, metal ou plástico.

Na ASEP existem duas gavetas conceituais:

- `RunRepository`, para execuções (`Run`);
- `TimelineRepository`, para eventos cronológicos (`TimelineEvent`).

`SQLiteRunRepository` e `SQLiteTimelineRepository` são implementações dessas
portas usando SQLite. SQLite é um banco de dados relacional armazenado em um
único arquivo local. Em uma analogia, ele é um caderno organizado: tabelas são
seções, linhas são registros e colunas identificam as informações necessárias.

## Explicação técnica

As portas são `Protocol` do Python. Um protocolo declara quais métodos um
objeto deve oferecer sem obrigar herança:

```python
class RunRepository(Protocol):
    def save(self, run: Run) -> None: ...
    def get(self, run_id: str) -> Run: ...
    def list(self) -> tuple[Run, ...]: ...


class TimelineRepository(Protocol):
    def append(self, event: TimelineEvent) -> None: ...
    def list_by_run(
        self,
        run_id: str,
    ) -> tuple[TimelineEvent, ...]: ...
```

As implementações SQLite cumprem esses contratos. `SQLiteRunRepository.save`
usa *upsert*: insere um Run novo ou substitui o snapshot que tem o mesmo `id`.
`SQLiteTimelineRepository.append` é append-only: adiciona um evento e rejeita
um `id` já existente.

Os objetos não são desmontados manualmente em dezenas de colunas. Os codecs
canônicos `RunCodec` e `TimelineEventCodec` geram um documento JSON, salvo na
coluna `payload`. Colunas separadas guardam chaves de identidade e consulta.
Esse desenho preserva todos os campos do domínio e reutiliza a mesma
serialização do backend em arquivo.

## Por que existe?

O backend em memória é rápido, mas perde tudo quando o processo termina. O
backend em arquivo JSON é durável, mas reescreve o documento inteiro a cada
alteração e não é adequado para consultas ou atualizações frequentes.

SQLite preenche o espaço entre esses dois:

- mantém dados depois do encerramento do processo;
- atualiza uma linha sem reescrever todos os Runs;
- possui transações;
- fornece chave primária e índice;
- não exige servidor de banco de dados;
- faz parte da biblioteca padrão do Python pelo módulo `sqlite3`.

O consumidor continua vendo apenas `RunRepository` e `TimelineRepository`.
Trocar o backend não muda `RunQueryService`, `MetricsService` ou Dashboard API.

## Como funciona?

Na construção de qualquer repository SQLite:

1. o caminho do banco é convertido em `Path`;
2. o diretório pai é criado;
3. `SQLiteDatabase` abre uma conexão;
4. o schema é criado com `CREATE TABLE IF NOT EXISTS`;
5. as colunas são verificadas com `PRAGMA table_info`;
6. a conexão de inicialização é fechada.

Em cada operação, uma nova conexão curta é aberta. O bloco transacional do
`sqlite3` confirma a alteração em sucesso (*commit*) ou a desfaz em erro
(*rollback*). A conexão é sempre fechada no final.

### Escrita de Run

1. `RunCodec.encode(run)` converte o modelo em tipos JSON;
2. `json.dumps` gera o payload determinístico;
3. `INSERT ... ON CONFLICT(id) DO UPDATE` grava o snapshot;
4. a transação é confirmada;
5. erros de serialização ou escrita viram erros tipados da ASEP.

### Leitura de Run

1. `SELECT payload FROM runs WHERE id = ?` procura o registro;
2. ausência gera `RunNotFoundError`;
3. `json.loads` lê o documento;
4. `RunCodec.decode` reconstrói e valida o modelo;
5. conteúdo inválido gera `InvalidRunStorageFormatError`.

### Escrita e leitura da Timeline

O evento é serializado pelo `TimelineEventCodec` e inserido com `INSERT`. Como
`id` é chave primária, uma duplicação é convertida em
`DuplicateTimelineEventError`. A consulta filtra por `run_id`; depois da
desserialização, eventos são ordenados por `timestamp` e `id`, preservando a
semântica dos demais backends mesmo quando timestamps usam offsets diferentes.

## Como a ASEP utiliza?

O sistema de configuração produz um `ApplicationSettings`. A Factory examina
`storage_backend`; quando ele é `sqlite`, cria os dois repositories apontando
para o mesmo arquivo:

```text
ApplicationSettings
        |
        v
RepositoryFactory
        |
        +--> SQLiteRunRepository --------+
        |                                |
        +--> SQLiteTimelineRepository ---+--> storage/asep.db
```

Serviços recebem as portas:

```text
RunQueryService
   |-- RunRepository
   `-- TimelineRepository

MetricsService ------> RunQueryService
Dashboard API -------> RunQueryService + MetricsService
```

Nenhum desses serviços importa `SQLiteRunRepository`,
`SQLiteTimelineRepository` ou `sqlite3`.

## Exemplo simples

Imagine uma biblioteca. O atendente pede “guarde este livro com o código 42”.
Ele não precisa conhecer o armário. A Factory escolhe o armário SQLite, que
coloca o livro em uma posição identificada. Se o atendente salvar novamente o
código 42, o registro é atualizado. O diário da biblioteca, por outro lado,
só aceita novas linhas e rejeita repetir o mesmo identificador.

Na ASEP, o Run é o livro e a Timeline é o diário.

## Exemplo técnico

Uso direto, útil para testes e ferramentas internas:

```python
from datetime import UTC, datetime
from pathlib import Path

from asep.runs import Run, SQLiteRunRepository
from asep.timeline import (
    SQLiteTimelineRepository,
    TimelineEvent,
    TimelineEventType,
)

database = Path("storage/asep.db")
run_repository = SQLiteRunRepository(database)
timeline_repository = SQLiteTimelineRepository(database)

run = Run(id="run-123", started_at=datetime.now(UTC))
run_repository.save(run)

event = TimelineEvent(
    id="event-123",
    run_id=run.id,
    timestamp=datetime.now(UTC),
    type=TimelineEventType.RUN_STARTED,
)
timeline_repository.append(event)

restored = run_repository.get("run-123")
events = timeline_repository.list_by_run("run-123")
```

Na composição normal, prefira a Factory:

```python
from asep.configuration import ApplicationSettings
from asep.repositories import RepositoryFactory

settings = ApplicationSettings(
    storage_backend="sqlite",
    sqlite_database="storage/asep.db",
)
repositories = RepositoryFactory(settings).create()
```

## Fluxo completo

```text
SALVAR RUN

Run
 |
 v
SQLiteRunRepository.save
 |
 +--> RunCodec.encode
 |         |
 |         v
 |      dict JSON
 |         |
 |         v
 |      json.dumps
 |         |
 v         v
SQLiteDatabase.connect
 |
 v
INSERT ... ON CONFLICT DO UPDATE
 |
 +--> sucesso --> COMMIT --> fechar conexão
 |
 `--> falha ----> ROLLBACK --> erro ASEP
```

```text
CONSULTAR TIMELINE

run_id
  |
  v
SELECT payload WHERE run_id = ?
  |
  v
TimelineEventCodec.decode
  |
  v
ordenar por datetime + id
  |
  v
tuple[TimelineEvent, ...]
```

## Diferenças entre os backends

| Característica | InMemory | File JSON | SQLite |
|---|---|---|---|
| Sobrevive ao processo | Não | Sim | Sim |
| Arquivo local | Não | Um JSON por tipo | Um banco compartilhado |
| Atualização de Run | Dicionário | Reescreve documento | Upsert de uma linha |
| Unicidade de evento | Código Python | Validação do arquivo | Chave primária |
| Transação do banco | Não | Substituição atômica | Sim |
| Consulta indexada | Não | Não | `run_id` da Timeline |
| Servidor externo | Não | Não | Não |
| Inspeção humana direta | Fácil no debugger | Fácil em editor | Exige ferramenta SQLite |

## Vantagens e casos de uso

SQLite é adequado para histórico local durável, Dashboard API local,
desenvolvimento, testes de integração e instalações de uma única máquina. O
mesmo banco pode ser reaberto por novas instâncias dos repositories.

É especialmente útil quando o volume já torna inconveniente reescrever um
arquivo JSON, mas operar PostgreSQL ou outro servidor seria complexidade
desnecessária.

## Possíveis erros

| Sintoma | Erro esperado | Diagnóstico e correção |
|---|---|---|
| Caminho é um diretório ou não pode ser aberto | `SQLiteConnectionError` | Confira `ASEP_SQLITE_DATABASE` e permissões |
| Arquivo não é um banco SQLite | `SQLiteSchemaError` | Preserve a evidência; use banco válido ou novo |
| Tabela tem colunas incompatíveis | `SQLiteSchemaError` | Não altere schema manualmente; restaure backup |
| Falha em `SELECT` | `RunStorageReadError` ou `TimelineStorageReadError` | Verifique integridade e acesso ao banco |
| Falha em `INSERT`/upsert | erro de escrita do repository | Verifique disco, locks e permissões |
| Payload de Run inválido | `InvalidRunStorageFormatError` | Preserve e investigue o registro |
| Evento repetido | `DuplicateTimelineEventError` | Gere um `event.id` globalmente único |
| Run não encontrado | `RunNotFoundError` | Confirme o `run_id` consultado |

Não edite o banco corrompido antes de copiá-lo. A cópia preserva evidência para
diagnóstico e possível recuperação.

## Como testar

Teste manual mínimo:

1. configure o backend conforme
   [SQLiteConfiguration](SQLiteConfiguration.md);
2. crie repositories pela Factory;
3. salve um Run e um evento;
4. encerre o processo;
5. crie novas instâncias apontando para o mesmo banco;
6. confirme `get`, `list` e `list_by_run`.

Testes automatizados relevantes:

```powershell
python -m pytest tests/test_sqlite_repository.py -v
python -m pytest tests/test_run_repository_contract.py -v
python -m pytest tests/test_timeline_repository_contract.py -v
python -m pytest tests/test_repository_factory.py -v
python -m pytest -v
```

Os testes de contrato executam a mesma expectativa contra memória, arquivo e
SQLite. Isso demonstra substituibilidade, princípio central do Repository
Pattern.

## Limitações atuais

- não existe pool de conexões;
- não existem migrations versionadas;
- não há ORM (Object-Relational Mapper);
- não há configuração de timeout ou pragmas avançados;
- não há API de exclusão;
- a Timeline não oferece paginação;
- o payload JSON não é consultável pela API dos repositories;
- não há política de backup, retenção ou compactação;
- concorrência distribuída e múltiplos hosts não são objetivo do SQLite local.

## Evolução futura

O contrato permite adicionar migrations, índices adicionais e observabilidade
sem mudar consumidores. Backends PostgreSQL ou outros podem implementar as
mesmas portas e ser registrados na Factory. Antes disso, devem ser definidos
versionamento de schema, política de backup, concorrência, retry e limites de
volume.

Documentos relacionados:

- [Schema do banco](DatabaseSchema.md)
- [Arquitetura SQLite](SQLiteArchitecture.md)
- [Configuração SQLite](SQLiteConfiguration.md)
- [Run Repository](../architecture/RunRepository.md)
- [Execution Timeline](../architecture/ExecutionTimeline.md)

## Relacionado a

- Sprint 7.5 e [Fase 07](../history/Phase-07.md)
- [ADR-016](../adr/ADR-016-sqlite-persistence.md)
- componentes `runs`, `timeline`, `repositories` e `sqlite`
- testes SQLite e contratos de repositories
- [Roadmap](../architecture/Roadmap.md) e
  [Architecture v1](../architecture/ASEP-Architecture-v1.md)
- [Glossário](../glossary/PersistenceGlossary.md)
