# Guia de migração da ASEP

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** validado para RC1

Este guia consolida o [Bootstrap](../../BOOTSTRAP.md) e o
[checklist operacional](../../project/MIGRATION_CHECKLIST.md).

## Pré-requisitos

- Git;
- CPython 3.12 ou superior;
- acesso ao repositório;
- Codex CLI somente para execução real do provider;
- espaço seguro para backup de dados locais.

## Clonagem e ambiente

```powershell
git clone https://github.com/paul-92/fabrica-de-software.git
cd fabrica-de-software
git switch feature/sprint-3-core-architecture
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

Em Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

Confirme o branch no [PROJECT_STATE](../../project/PROJECT_STATE.md), pois o
nome pode mudar após publicação do RC1.

## Configuração

Defaults funcionam sem variáveis. `.env.example` é referência; a aplicação não
carrega `.env` automaticamente. Configure o shell/IDE quando necessário:

```powershell
$env:ASEP_STORAGE_BACKEND = "sqlite"
$env:ASEP_SQLITE_DATABASE = "storage/asep.db"
```

Backends: `memory`, `file`, `sqlite`. O backend file também aceita nomes
customizados para Runs, Timeline e WorkflowSnapshots.

## Validação

```powershell
python scripts/verify_environment.py
python -m pytest -v --basetemp=qa-runtime-temp/clean-clone
python -m pytest --cov=asep --cov-report=term
python -m compileall src tests
git diff --check
```

Resultado de referência do RC1: 665 testes e 95% de cobertura.

## Execução

```powershell
asep --help
asep run projects/asep-self-development
python -m uvicorn asep.api.composition:create_default_app --factory --host 127.0.0.1 --port 8000
```

Health check: `http://127.0.0.1:8000/api/v1/health`.

## Backup SQLite

Pare a aplicação. Para cópia simples:

```powershell
Copy-Item -LiteralPath storage/asep.db -Destination <BACKUP_SEGURO>
```

Com o cliente SQLite disponível:

```powershell
sqlite3 storage/asep.db ".backup '<BACKUP_SEGURO>/asep.db'"
```

Copie também `.asep`, `artifacts/runs` e `logs/runs` somente se o histórico
local for necessário e autorizado.

## Recuperação

1. valide checksum/tamanho do backup;
2. mantenha a aplicação parada;
3. restaure o arquivo no path configurado;
4. execute testes de repository e consultas;
5. valide Runs, Timeline, Metrics e Dashboard;
6. preserve o backup até concluir a comparação.

WorkflowSnapshots são históricos; não implementam retomada automática.

## Boas práticas

- nunca transfira `.env` ou credenciais pelo Git;
- não copie `.venv` entre máquinas;
- não apague a origem antes de validar commits e dados;
- use paths curtos e com permissão para temporários no Windows;
- execute scanner de histórico Git antes do release;
- documente qualquer diferença do ambiente novo.

