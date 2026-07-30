# Arquitetura do backend SQLite

**Público:** pessoas desenvolvedoras iniciantes e experientes  
**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** vigente desde a Sprint 7.5

## O que é?

A arquitetura SQLite é a organização das peças que leva uma solicitação da
aplicação até o arquivo do banco, sem fazer a aplicação depender de SQLite.

Uma analogia:

- Configuration é o painel que informa qual armazenamento usar;
- RepositoryFactory é a pessoa que escolhe o armário;
- interfaces são etiquetas padronizadas nas gavetas;
- repositories SQLite são os funcionários que sabem operar o armário;
- `SQLiteDatabase` é a chave e o manual de montagem;
- `asep.db` é o armário físico.

Cada peça possui uma responsabilidade pequena e definida.

## Explicação técnica

A arquitetura combina quatro padrões:

1. **Configuration Object:** `ApplicationSettings` é um snapshot imutável.
2. **Factory Pattern:** `RepositoryFactory` seleciona implementações concretas.
3. **Repository Pattern:** serviços dependem de portas de persistência.
4. **Adapter:** repositories traduzem modelos de domínio para `sqlite3`.

```text
camada de entrada/composição
        |
        v
Configuration.load -> ApplicationSettings
        |
        v
RepositoryFactory
        |
        +-----------------------------+
        |                             |
        v                             v
SQLiteRunRepository       SQLiteTimelineRepository
        |                             |
        +--------------+--------------+
                       v
                 SQLiteDatabase
                       |
                       v
                    sqlite3
                       |
                       v
               storage/asep.db
```

Os serviços de aplicação permanecem acima dessa estrutura e recebem apenas
`RunRepository` e `TimelineRepository`.

## Por que existe?

Sem separação, `RunQueryService` precisaria abrir conexões, conhecer SQL,
decodificar JSON e tratar erros do SQLite. Isso misturaria regra de consulta
com infraestrutura, dificultaria testes e impediria trocar o backend.

A arquitetura resolve:

- seleção central do backend;
- isolamento de SQL e conexão;
- reuso do schema pelos dois repositories;
- substituição por memória ou arquivo nos testes;
- evolução futura sem alteração dos consumidores;
- tratamento de erros em termos da ASEP.

## Como funciona?

### Camada de configuração

`Configuration.load()` combina defaults e variáveis de ambiente e cria
`ApplicationSettings`. O modelo é `frozen`, isto é, não pode ser alterado após
a construção.

Para SQLite interessam:

- `storage_backend = StorageBackend.SQLITE`;
- `sqlite_database = Path("storage/asep.db")`.

### Camada de Factory

`RepositoryFactory.create()` mantém um registro de builders por
`StorageBackend`. O builder SQLite cria os dois adapters usando o mesmo caminho.
A Factory conhece classes concretas; consumidores não conhecem.

### Camada de repositories

`SQLiteRunRepository` conhece:

- contrato de Run;
- `RunCodec`;
- SQL da tabela `runs`;
- tradução de erros de leitura/escrita.

`SQLiteTimelineRepository` conhece:

- contrato de Timeline;
- `TimelineEventCodec`;
- SQL de `timeline_events`;
- unicidade e consulta por Run.

Um não chama o outro.

### Camada de conexão

`SQLiteDatabase` centraliza:

- criação do diretório;
- abertura e fechamento da conexão;
- `row_factory` para acesso por nome;
- contexto transacional;
- criação do schema e índice;
- validação das colunas.

Ela não conhece `Run`, `TimelineEvent`, Factory, API ou Metrics.

### Camada do driver

`sqlite3` é o driver da biblioteca padrão do Python. Ele comunica com o arquivo
SQLite. Não há SQLAlchemy, ORM, Alembic nem serviço externo.

## Como a ASEP utiliza?

O composition root da Dashboard API faz:

```text
create_default_app
       |
       v
Configuration.load
       |
       v
RepositoryFactory.create
       |
       +--> RunRepository
       `--> TimelineRepository
                 |
                 v
          RunQueryService
                 |
          +------+------+
          |             |
          v             v
   MetricsService   Dashboard API
```

O mesmo `RunQueryService` funciona com qualquer backend. Essa
substituibilidade é validada pelos testes de contrato.

Uma observação importante: o backend padrão continua sendo `memory`. SQLite é
selecionado explicitamente por configuração.

## Responsabilidades e fronteiras

| Componente | Responsável por | Não responsável por |
|---|---|---|
| `Configuration` | ler defaults/ambiente | abrir banco |
| `ApplicationSettings` | validar e transportar valores | escolher classes |
| `RepositoryFactory` | selecionar e construir adapters | executar consultas |
| `SQLiteDatabase` | conexão, transação e schema | serializar domínio |
| `SQLiteRunRepository` | persistir Runs | métricas e HTTP |
| `SQLiteTimelineRepository` | persistir eventos | lifecycle do workflow |
| `RunQueryService` | consultas de aplicação | SQL e conexão |
| `MetricsService` | derivar métricas | persistir registros |
| Dashboard API | transporte HTTP somente leitura | escolher backend concreto |

Dependências apontam da composição para os adapters, e dos adapters para
infraestrutura/domínio. `sqlite` não é importado por serviços.

## Exemplo simples

Uma loja recebe pedidos no balcão. O vendedor trabalha com a ideia de
“estoque”, não com o mecanismo do depósito. O gerente (Factory) escolhe o
depósito SQLite conforme o painel (Configuration). O estoquista especializado
(repository) traduz “guarde este produto” para as operações do depósito. A
equipe de manutenção (`SQLiteDatabase`) cuida da porta, prateleiras e chave.

Trocar o depósito por memória durante um teste não muda o trabalho do vendedor.

## Exemplo técnico

Composição manual:

```python
from asep.application import RunQueryService
from asep.configuration import Configuration
from asep.metrics import MetricsService
from asep.repositories import RepositoryFactory

settings = Configuration.load(
    {
        "ASEP_STORAGE_BACKEND": "sqlite",
        "ASEP_SQLITE_DATABASE": "storage/asep.db",
    }
)
bundle = RepositoryFactory(settings).create()

query_service = RunQueryService(
    bundle.run_repository,
    bundle.timeline_repository,
)
metrics_service = MetricsService(query_service)
```

Com variáveis no PowerShell:

```powershell
$env:ASEP_STORAGE_BACKEND = "sqlite"
$env:ASEP_SQLITE_DATABASE = "storage/asep.db"
python -m uvicorn asep.api.composition:create_default_app --factory
```

O código da API não precisa receber a palavra `sqlite`: a configuração e a
Factory resolvem a implementação.

## Fluxo completo

### Inicialização da aplicação

```text
processo inicia
    |
    v
ler ASEP_* (ou defaults)
    |
    v
validar ApplicationSettings
    |
    v
Factory consulta storage_backend
    |
    +--> memory --> repositories em memória
    |
    +--> file ----> repositories JSON
    |
    `--> sqlite --> dois repositories
                         |
                         v
                  SQLiteDatabase(path)
                         |
               +---------+----------+
               |                    |
               v                    v
          criar schema        validar schema
               |                    |
               +---------+----------+
                         v
                  serviços prontos
```

### Operação de escrita

```text
serviço/caso de uso
       |
       v
porta do repository
       |
       v
adapter SQLite
       |
       +--> codec --> JSON
       |
       v
SQLiteDatabase.connect
       |
       v
SQL parametrizado
       |
       +--> sucesso: commit
       `--> erro: rollback + exceção tipada
       |
       v
fechar conexão
```

### Operação de leitura

```text
consulta
   |
   v
SQL SELECT parametrizado
   |
   v
sqlite3.Row
   |
   v
JSON -> codec -> modelo validado
   |
   v
snapshot devolvido ao serviço
```

## Decisões arquiteturais

- **Uma conexão por operação:** simples, determinística e adequada ao escopo
  local; evita manter recursos globais abertos.
- **Um banco para os dois repositories:** configuração e backup simples.
- **Payload JSON canônico:** preserva contrato e reduz duplicação.
- **Colunas auxiliares:** identidade e consulta não exigem interpretar JSON.
- **Ordenação após decode:** respeita `datetime` com timezone/offset.
- **Schema automático:** primeira execução funciona sem etapa administrativa.
- **Validação estrita de colunas:** falha cedo diante de banco incompatível.
- **Sem foreign key:** preserva independência e ordem atual de gravação.
- **Erros tipados:** detalhes de `sqlite3` não vazam como API principal.

## Possíveis erros

### Configuração

Backend desconhecido, caminho vazio ou valor inválido geram
`ConfigurationValidationError`. Corrija `ASEP_STORAGE_BACKEND` ou
`ASEP_SQLITE_DATABASE`.

### Conexão

Diretório sem permissão, caminho que aponta para uma pasta ou falha de abertura
geram `SQLiteConnectionError`. Confirme caminho, permissões e espaço.

### Schema

Arquivo de outro formato, tabela alterada ou banco ilegível geram
`SQLiteSchemaError`. Preserve o arquivo antes de qualquer recuperação.

### Operação

Falhas de SQL são traduzidas em erros de leitura/escrita dos repositories.
Duplicação de evento vira `DuplicateTimelineEventError`; Run ausente vira
`RunNotFoundError`; payload inválido usa os erros de formato existentes.

## Como testar

Pirâmide de testes:

```text
                 +----------------------+
                 | Dashboard/integração |
              +--+----------------------+--+
              | Factory + Configuration    |
           +--+-----------------------------+--+
           | contratos Run/Timeline            |
        +--+------------------------------------+--+
        | conexão, schema, codecs e erros          |
        +-------------------------------------------+
```

Comandos:

```powershell
python -m pytest tests/test_sqlite_repository.py -v
python -m pytest tests/test_configuration.py -v
python -m pytest tests/test_repository_factory.py -v
python -m pytest tests/test_dashboard_api.py -v
python -m pytest -v
python -m compileall src tests
git diff --check
```

Para um teste manual, use um diretório descartável, salve registros, encerre o
processo e consulte por uma nova instância. Nunca use o banco de produção em
testes destrutivos.

## Limitações atuais

- sem IoC Container ou framework de injeção;
- sem pool de conexões;
- sem tuning de pragmas;
- sem migrations versionadas;
- sem observabilidade de duração das queries;
- sem retry de `database is locked`;
- sem backup/restore automatizado;
- sem transação coordenada entre salvar Run e adicionar evento;
- sem suporte distribuído ou servidor remoto;
- schema validado apenas pelo conjunto de colunas.

## Evolução futura

A próxima evolução pode introduzir uma porta de conexão, migrations e
telemetria sem afetar serviços. PostgreSQL ou outro backend deve entrar como
novo adapter e novo valor registrado na Factory. Um IoC Container só se
justifica se a composição manual se tornar complexa; não é requisito atual.

Antes de aumentar concorrência, devem ser definidos timeout, WAL (*Write-Ahead
Logging*), retry e consistência entre Run e Timeline. Antes de migrations, deve
existir versionamento explícito e política de rollback.

Documentos relacionados:

- [Repositórios SQLite](SQLiteRepositories.md)
- [Schema](DatabaseSchema.md)
- [Configuração](SQLiteConfiguration.md)
- [Arquitetura geral](../architecture/ASEP-Architecture-v1.md)

## Relacionado a

- Sprint 7.5 e [Fase 07](../history/Phase-07.md)
- [ADR-016](../adr/ADR-016-sqlite-persistence.md)
- Configuration, Factory, repository protocols, adapters e conexão
- testes de Factory, configuração, contratos e integração
- [Roadmap](../architecture/Roadmap.md) e
  [Glossário](../glossary/PersistenceGlossary.md)
