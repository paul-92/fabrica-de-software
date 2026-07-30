# Schema do banco SQLite da ASEP

**Público:** pessoas desenvolvedoras iniciantes e experientes  
**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** vigente desde a Sprint 7.5

## O que é?

Schema é a planta do banco de dados. Assim como a planta de uma casa define
quais cômodos existem, o schema define tabelas, colunas, tipos, chaves e
índices.

O banco SQLite da ASEP contém duas tabelas:

- `runs`, com o último snapshot conhecido de cada execução;
- `timeline_events`, com os acontecimentos associados às execuções.

Ele também possui um índice para localizar rapidamente eventos pelo `run_id`.

## Explicação técnica

O schema real é criado por `SQLiteDatabase`:

```sql
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS timeline_events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_timeline_events_run
    ON timeline_events (run_id);
```

`TEXT` é um tipo de afinidade do SQLite para texto. `NOT NULL` impede ausência
do valor. `PRIMARY KEY` identifica uma linha de forma única. Um índice é uma
estrutura auxiliar que acelera buscas, semelhante ao índice remissivo de um
livro.

Os campos completos de domínio ficam no `payload` JSON. Isso é intencional:
colunas operacionais suportam identidade e seleção; o codec canônico preserva o
objeto inteiro.

## Por que existe?

Sem schema, cada gravação poderia assumir uma estrutura diferente. O schema
oferece garantias mínimas:

- um Run tem identificador único;
- um evento tem identificador único;
- todo evento informa seu Run;
- timestamps e payloads são obrigatórios;
- eventos podem ser filtrados por Run com índice;
- uma estrutura incompatível é detectada na inicialização.

A verificação evita operar silenciosamente sobre tabelas criadas por outra
versão ou por intervenção manual.

## Como funciona?

Ao abrir o repository, `SQLiteDatabase` executa o script idempotente.
Idempotente significa que repetir a inicialização produz o mesmo resultado:
`IF NOT EXISTS` não apaga nem recria tabelas válidas.

Depois, para cada tabela:

1. executa `PRAGMA table_info(nome_da_tabela)`;
2. coleta os nomes das colunas;
3. compara com o conjunto esperado;
4. levanta `SQLiteSchemaError` se houver coluna ausente ou extra.

Essa é uma validação estrutural simples. Ela não é um sistema de migrations e
não transforma bancos antigos.

## Como a ASEP utiliza?

Ambos os repositories usam o mesmo arquivo e a mesma infraestrutura:

```text
                    asep.db
                       |
          +------------+-------------+
          |                          |
          v                          v
       runs                   timeline_events
          ^                          ^
          |                          |
SQLiteRunRepository      SQLiteTimelineRepository
```

Não existe chave estrangeira declarada entre as tabelas. `timeline_events.run_id`
é uma associação lógica com `runs.id`, mas a Timeline pode registrar eventos
mesmo que o Run ainda não esteja na tabela `runs`. Isso mantém o contrato atual
dos repositories e evita acoplamento de ordem entre gravações.

## Estrutura detalhada

### Tabela `runs`

```text
+------------+------+----------+---------------------------------------+
| Coluna     | Tipo | Regra    | Finalidade                            |
+------------+------+----------+---------------------------------------+
| id         | TEXT | PK       | Identificador único do Run            |
| started_at | TEXT | NOT NULL | Timestamp ISO 8601 para apoio técnico |
| payload    | TEXT | NOT NULL | Documento JSON completo do Run        |
+------------+------+----------+---------------------------------------+
```

`id` é a chave primária (PK, *Primary Key*). Um novo `save` com o mesmo `id`
atualiza `started_at` e `payload`; não cria uma segunda linha.

`started_at` usa `datetime.isoformat()`. O timezone é obrigatório no modelo de
domínio. A ordenação oficial não depende da ordem textual desta coluna: o
repository desserializa os Runs e ordena pelos objetos `datetime`, depois por
`id`. Isso preserva a ordem correta entre offsets diferentes.

`payload` contém:

```json
{
  "error": null,
  "finished_at": null,
  "id": "run-123",
  "metadata": {},
  "project_id": "project",
  "provider_name": "codex",
  "stage_id": "analysis",
  "started_at": "2026-07-30T12:00:00Z",
  "status": "running",
  "summary": null,
  "workflow_id": "default"
}
```

As chaves são produzidas pelo `RunCodec`; o exemplo pode variar conforme os
valores reais, mas não contém objetos Python.

### Tabela `timeline_events`

```text
+-----------+------+----------+----------------------------------------+
| Coluna    | Tipo | Regra    | Finalidade                             |
+-----------+------+----------+----------------------------------------+
| id        | TEXT | PK       | Identificador global único do evento   |
| run_id    | TEXT | NOT NULL | Run associado e chave de consulta      |
| timestamp | TEXT | NOT NULL | Timestamp ISO 8601 do evento           |
| payload   | TEXT | NOT NULL | Documento JSON completo do evento      |
+-----------+------+----------+----------------------------------------+
```

O `id` globalmente único implementa a regra append-only. Uma tentativa de
inserir o mesmo valor viola a chave primária e se torna
`DuplicateTimelineEventError`.

`run_id` é filtrado por igualdade. O índice `idx_timeline_events_run` permite
ao SQLite localizar as linhas sem varrer necessariamente toda a tabela.

O payload típico é:

```json
{
  "id": "event-123",
  "message": "Execution started",
  "metadata": {"attempt": 1},
  "run_id": "run-123",
  "stage_id": null,
  "timestamp": "2026-07-30T12:00:00Z",
  "type": "run.started"
}
```

### Relacionamento lógico

```text
runs                              timeline_events
+----------------+                +----------------------+
| PK id          |<...............| run_id               |
| started_at     |  associação    | PK id                |
| payload        |  lógica        | timestamp            |
+----------------+  sem FK        | payload              |
                                  +----------------------+

Um Run pode possuir zero, um ou muitos eventos.
Um evento referencia exatamente um run_id textual.
```

FK significa *Foreign Key*, ou chave estrangeira. A linha pontilhada indica que
o relacionamento não é imposto pelo banco nesta versão.

## Exemplo simples

Pense em uma planilha com duas abas. A aba `runs` tem uma linha por execução.
A aba `timeline_events` tem várias linhas do diário. A coluna `run_id` diz a
qual execução cada linha do diário pertence. O `payload` é um envelope com
todos os detalhes, mesmo os que não ganharam coluna própria.

## Exemplo técnico

Inspeção segura, somente leitura, com a CLI `sqlite3` quando instalada:

```text
sqlite3 storage/asep.db
.tables
.schema runs
.schema timeline_events
SELECT id, started_at FROM runs;
SELECT id, run_id, timestamp FROM timeline_events;
.quit
```

Inspeção com Python, sem ferramenta externa:

```python
import sqlite3

with sqlite3.connect("storage/asep.db") as connection:
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    columns = connection.execute(
        "PRAGMA table_info(runs)"
    ).fetchall()
```

Use parâmetros em dados fornecidos externamente:

```python
row = connection.execute(
    "SELECT payload FROM runs WHERE id = ?",
    (run_id,),
).fetchone()
```

O `?` evita concatenar o valor na instrução SQL.

## Fluxo completo

```text
INICIALIZAÇÃO

caminho do banco
      |
      v
criar diretório pai
      |
      v
sqlite3.connect
      |
      v
CREATE TABLE/INDEX IF NOT EXISTS
      |
      v
PRAGMA table_info
      |
      +--> colunas esperadas --> banco pronto
      |
      `--> divergência --------> SQLiteSchemaError
```

```text
UPsert DE RUN

Run --> RunCodec --> JSON --> INSERT
                               |
                     id já existe?
                      /          \
                    não          sim
                    |             |
                  INSERT        UPDATE
                      \          /
                         COMMIT
```

```text
CONSULTA DE EVENTOS

run_id --> índice idx_timeline_events_run
             |
             v
         linhas do Run
             |
             v
       decodificar payload
             |
             v
       ordenar datetime + id
```

## Possíveis erros

- `SQLiteConnectionError`: banco não pôde ser aberto ou diretório não pôde ser
  criado.
- `SQLiteSchemaError`: arquivo não é SQLite, SQL de inicialização falhou ou
  colunas não correspondem ao schema esperado.
- `InvalidRunStorageFormatError`: payload do Run não é JSON/Run válido.
- `InvalidTimelineStorageFormatError`: payload do evento não é válido.
- erros de leitura/escrita: falha operacional após a inicialização.
- `DuplicateTimelineEventError`: chave primária de evento repetida.

Para diagnosticar:

1. copie o banco antes de modificá-lo;
2. confirme o caminho efetivo;
3. verifique permissões e espaço em disco;
4. execute `PRAGMA integrity_check` em uma cópia;
5. compare `.schema` com este documento;
6. não adicione colunas manualmente: a validação atual exige conjunto exato.

## Como testar

Teste automatizado do schema:

```powershell
python -m pytest tests/test_sqlite_repository.py -v
```

O teste cria um banco temporário, consulta `sqlite_master` e confirma as duas
tabelas. Outro teste cria uma tabela incompatível e espera
`SQLiteSchemaError`.

Teste manual:

1. remova apenas um banco descartável de teste;
2. construa `SQLiteRunRepository` apontando para ele;
3. confirme que o arquivo foi criado;
4. liste tabelas e colunas;
5. salve um Run e um evento;
6. consulte as colunas operacionais e os payloads;
7. reabra os repositories e confirme os modelos.

## Limitações atuais

- schema tem versão implícita, não uma tabela de versão;
- não há migrations incrementais;
- não há chave estrangeira;
- não há colunas individuais para status, provider ou tipo de evento;
- consultas internas ao JSON não fazem parte do contrato;
- timestamps ficam em texto e a ordenação de domínio ocorre após decode;
- não há triggers, views ou política de retenção;
- a validação compara nomes de colunas, não todos os detalhes de afinidade,
  constraints ou índice.

## Evolução futura

Uma evolução segura pode adicionar tabela `schema_version`, migrations
numeradas, constraints e índices orientados por métricas reais. Extrair campos
do payload para colunas exige estratégia de compatibilidade e backfill. Chaves
estrangeiras só devem ser adicionadas depois de definir a ordem transacional
entre Run e Timeline.

Documentos relacionados:

- [Repositórios SQLite](SQLiteRepositories.md)
- [Arquitetura SQLite](SQLiteArchitecture.md)
- [Configuração SQLite](SQLiteConfiguration.md)

## Relacionado a

- Sprint 7.5 e [Fase 07](../history/Phase-07.md)
- [ADR-016](../adr/ADR-016-sqlite-persistence.md)
- `SQLiteDatabase`, `SQLiteRunRepository` e `SQLiteTimelineRepository`
- `tests/test_sqlite_repository.py`
- [Roadmap](../architecture/Roadmap.md),
  [Architecture](../architecture/ASEP-Architecture-v1.md) e
  [Glossário](../glossary/PersistenceGlossary.md)
