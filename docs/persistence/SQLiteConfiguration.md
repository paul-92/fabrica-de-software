# Configuração do SQLite na ASEP

**Público:** pessoas operadoras e desenvolvedoras iniciantes ou experientes  
**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** vigente desde a Sprint 7.5

## O que é?

Configuração é o painel de opções da aplicação. Em vez de alterar código para
escolher onde os dados serão guardados, a pessoa operadora define variáveis de
ambiente.

Uma variável de ambiente é um par nome/valor fornecido pelo sistema operacional
ao processo. Para SQLite, a ASEP usa:

- `ASEP_STORAGE_BACKEND`, que escolhe o tipo de armazenamento;
- `ASEP_SQLITE_DATABASE`, que define o arquivo do banco.

## Explicação técnica

`Configuration.load()` lê um `Mapping` ou, por padrão, `os.environ`. Valores
presentes sobrescrevem defaults. O resultado é um `ApplicationSettings`
imutável e validado.

| Configuração | Variável | Default |
|---|---|---|
| backend | `ASEP_STORAGE_BACKEND` | `memory` |
| banco SQLite | `ASEP_SQLITE_DATABASE` | `storage/asep.db` |

Os demais valores continuam disponíveis:

| Variável | Default | Uso |
|---|---|---|
| `ASEP_STORAGE_DIRECTORY` | `storage` | backend `file` |
| `ASEP_RUNS_FILENAME` | `runs.json` | arquivo de Runs |
| `ASEP_TIMELINE_FILENAME` | `timeline-events.json` | arquivo da Timeline |
| `ASEP_WORKFLOWS_FILENAME` | `workflow-snapshots.json` | snapshots no backend file |

Para ativar SQLite, o backend deve ser exatamente `sqlite`, em letras
minúsculas. Definir apenas o caminho do banco não muda o backend padrão.

## Por que existe?

Valores fixos espalhados obrigariam editar e republicar código para trocar um
caminho. O sistema central:

- mantém defaults em um ponto;
- permite configuração por ambiente;
- valida antes de construir repositories;
- entrega o mesmo snapshot a toda a composição;
- evita que serviços leiam diretamente `os.environ`;
- prepara a adição de novas opções sem criar configuração global mutável.

## Como funciona?

Precedência desta sprint:

```text
variável de ambiente presente
            |
       sim / \ não
          /   \
         v     v
 valor informado  valor padrão
          \       /
           v     v
      ApplicationSettings
              |
              v
      validação + imutabilidade
              |
              v
       RepositoryFactory
```

Não há leitura de `.env`, YAML, TOML, JSON de configuração ou argumentos de
CLI. Um arquivo chamado `.env` não é carregado automaticamente.

### Validação

`storage_backend` aceita `memory`, `file` ou `sqlite`. Comparação é estrita:
`SQLite`, `SQLITE` e valores com espaços são inválidos.

`sqlite_database` aceita `str` ou `Path`, mas texto vazio ou apenas espaços é
inválido. O caminho é convertido em `Path`. O diretório pai é criado pelo
`SQLiteDatabase` quando possível.

O objeto é uma dataclass `frozen`; tentar alterar um campo depois da criação
gera `FrozenInstanceError`.

## Como a ASEP utiliza?

Na Dashboard API:

```text
ambiente do processo
        |
        v
Configuration.load()
        |
        v
ApplicationSettings
        |
        v
RepositoryFactory
        |
        v
SQLite repositories
```

`application.query_composition` segue o mesmo princípio. Configuração é lida no
composition root, não dentro de `RunQueryService`, `MetricsService` ou rotas.

Também é possível fornecer `ApplicationSettings` explicitamente em testes:

```python
app = create_default_app(
    ApplicationSettings(
        storage_backend="sqlite",
        sqlite_database="test-data/asep.db",
    )
)
```

## Exemplo simples

Imagine uma impressora com dois controles: “tipo de papel” e “bandeja”. O
primeiro escolhe SQLite; o segundo informa onde está o arquivo. Se nenhum
controle for alterado, a aplicação continua no modo padrão em memória.

Configuração correta:

```text
tipo de armazenamento = sqlite
arquivo do banco       = storage/asep.db
```

## Exemplo técnico

### PowerShell — sessão atual

```powershell
$env:ASEP_STORAGE_BACKEND = "sqlite"
$env:ASEP_SQLITE_DATABASE = "storage/asep.db"
```

As variáveis valem para processos iniciados a partir dessa sessão. Para
verificar:

```powershell
Write-Output $env:ASEP_STORAGE_BACKEND
Write-Output $env:ASEP_SQLITE_DATABASE
```

Para remover da sessão:

```powershell
Remove-Item Env:ASEP_STORAGE_BACKEND
Remove-Item Env:ASEP_SQLITE_DATABASE
```

### Linux/macOS — shell atual

```bash
export ASEP_STORAGE_BACKEND=sqlite
export ASEP_SQLITE_DATABASE=storage/asep.db
```

Para remover:

```bash
unset ASEP_STORAGE_BACKEND
unset ASEP_SQLITE_DATABASE
```

### Carregamento explícito em Python

```python
from asep.configuration import Configuration

settings = Configuration.load(
    {
        "ASEP_STORAGE_BACKEND": "sqlite",
        "ASEP_SQLITE_DATABASE": "storage/asep.db",
    }
)

assert settings.storage_backend.value == "sqlite"
assert str(settings.sqlite_database) == "storage/asep.db"
```

### Caminho absoluto

Windows:

```powershell
$env:ASEP_SQLITE_DATABASE = "C:\asep-data\asep.db"
```

Linux/macOS:

```bash
export ASEP_SQLITE_DATABASE=/var/lib/asep/asep.db
```

O usuário do processo precisa de permissão para criar o diretório/arquivo e
ler/escrever o banco.

## Fluxo completo

```text
PROCESSO ASEP
    |
    v
Configuration.load()
    |
    +--> ASEP_STORAGE_BACKEND existe?
    |        | sim: usar valor
    |        ` não: "memory"
    |
    +--> ASEP_SQLITE_DATABASE existe?
    |        | sim: usar caminho
    |        ` não: "storage/asep.db"
    |
    v
ApplicationSettings.__post_init__()
    |
    +--> validar backend
    +--> validar caminho não vazio
    +--> converter para Path
    |
    v
snapshot frozen
    |
    v
RepositoryFactory
    |
    `--> backend sqlite --> abrir/criar banco
```

### O que acontece com caminhos relativos?

`storage/asep.db` é relativo ao diretório de trabalho do processo. Se o
processo iniciar em outro diretório, o local efetivo muda:

```text
cwd = C:\projeto
config = storage/asep.db
resultado = C:\projeto\storage\asep.db
```

Para serviços iniciados por ferramentas distintas, prefira caminho absoluto ou
controle explicitamente o diretório de trabalho.

## Boas práticas

- use banco diferente para desenvolvimento, testes e operação;
- prefira caminho absoluto em serviços e automações;
- não armazene o banco dentro de diretório temporário se precisar de histórico;
- garanta backup antes de upgrades ou inspeções invasivas;
- restrinja permissões do arquivo aos usuários necessários;
- não compartilhe o mesmo arquivo em filesystem de rede sem avaliar suporte;
- não registre payloads ou caminhos sensíveis desnecessariamente em logs;
- use diretórios temporários fornecidos pelo pytest nos testes;
- não altere o schema manualmente;
- mantenha `ASEP_STORAGE_BACKEND` e `ASEP_SQLITE_DATABASE` no mesmo escopo de
  processo.

## Possíveis erros

### Backend inválido

```text
ASEP_STORAGE_BACKEND=SQLite
```

Resultado: `ConfigurationValidationError` com backend não suportado. Correção:
use `sqlite`.

### Caminho vazio

```text
ASEP_SQLITE_DATABASE=
```

Resultado: configuração inválida. Correção: remova a variável para usar o
default ou informe um caminho.

### Caminho aponta para diretório

Se `ASEP_SQLITE_DATABASE` apontar para uma pasta existente, a abertura falha
com `SQLiteConnectionError`. Informe o nome do arquivo, por exemplo
`storage/asep.db`.

### Permissão ou disco

Falha ao criar o diretório ou abrir o banco produz erro de conexão. Confirme
permissões, espaço livre e propriedade do diretório.

### Banco incompatível

Um arquivo que não seja SQLite ou tenha schema diferente produz
`SQLiteSchemaError`. Não sobrescreva. Copie o arquivo e investigue.

### Variável não foi aplicada

Confirme:

1. a variável foi definida antes de iniciar o processo;
2. o processo é filho da sessão configurada;
3. não há erro de digitação no prefixo `ASEP_`;
4. o backend também foi definido como `sqlite`;
5. no Windows, verifique a sessão correta do terminal.

## Como testar

Teste automatizado:

```powershell
python -m pytest tests/test_configuration.py -v
python -m pytest tests/test_repository_factory.py -v
python -m pytest tests/test_sqlite_repository.py -v
```

O teste deve fornecer um mapping ou usar `monkeypatch`; nunca depende das
variáveis reais da máquina.

Teste manual em diretório descartável:

```powershell
$env:ASEP_STORAGE_BACKEND = "sqlite"
$env:ASEP_SQLITE_DATABASE = ".local-test\asep.db"
python -c "from asep.configuration import Configuration; print(Configuration.load())"
```

Depois de uma composição que inicialize repositories, confirme a existência de
`.local-test\asep.db`. Remova somente se for um banco descartável conhecido.

## Limitações atuais

- sem arquivo `.env`;
- sem configuração YAML, TOML ou JSON;
- sem flags de CLI;
- sem reload dinâmico;
- sem configuração por projeto;
- sem segredo/credential store (SQLite local não exige credenciais);
- sem validação de writability durante a construção de `ApplicationSettings`;
- sem configuração de timeout, journal mode, cache ou pragmas;
- sem expansão especial de `~` ou variáveis embutidas no caminho;
- o caminho relativo depende do diretório de trabalho.

## Evolução futura

Fontes adicionais podem alimentar o mesmo `ApplicationSettings`, desde que a
precedência seja documentada. Configurações futuras podem incluir timeout,
modo WAL, política de backup e caminhos por ambiente.

Adicionar PostgreSQL exigirá novos campos, possivelmente sensíveis. Eles devem
ser validados sem expor credenciais em erros ou logs. A Factory continuará
recebendo apenas o snapshot imutável.

Documentos relacionados:

- [Arquitetura SQLite](SQLiteArchitecture.md)
- [Repositórios SQLite](SQLiteRepositories.md)
- [Schema](DatabaseSchema.md)
- [Arquitetura geral](../architecture/ASEP-Architecture-v1.md)

## Relacionado a

- Sprint 7.5 e [Fase 07](../history/Phase-07.md)
- [ADR-016](../adr/ADR-016-sqlite-persistence.md)
- `Configuration`, `ApplicationSettings` e `RepositoryFactory`
- `tests/test_configuration.py` e `tests/test_repository_factory.py`
- [Roadmap](../architecture/Roadmap.md) e
  [Glossário](../glossary/PersistenceGlossary.md)
