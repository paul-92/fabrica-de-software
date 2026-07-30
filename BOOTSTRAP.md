# Bootstrap da ASEP

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente em 2026-07-30

## Pré-requisitos

- Git;
- Python 3.12 ou superior (ambiente validado: CPython 3.14.4, 64-bit);
- acesso ao repositório remoto;
- Codex CLI apenas para execução real do `CodexProvider`; testes não dependem dele.

O projeto usa `pip`, `venv`, `pyproject.toml` e setuptools. Não há lockfile.

## Clonar e selecionar o branch

```powershell
git clone https://github.com/paul-92/fabrica-de-software.git
cd fabrica-de-software
git switch feature/sprint-3-core-architecture
```

Confirme em [project/PROJECT_STATE.md](project/PROJECT_STATE.md) se o branch
mudou depois desta fotografia.

## Windows

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
Copy-Item .env.example .env
```

Se Python 3.14 não estiver disponível, use qualquer CPython suportado por
`pyproject.toml` (`>=3.12`) e execute a suíte completa.

## Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
cp .env.example .env
```

O código é multiplataforma; a validação desta fotografia ocorreu no Windows 11.

## Configuração

A aplicação não carrega `.env` automaticamente. O arquivo é um modelo para
exportar as variáveis no shell ou configurar a IDE. Defaults funcionam sem
variáveis. Consulte
[SQLiteConfiguration](docs/persistence/SQLiteConfiguration.md).

PowerShell:

```powershell
$env:ASEP_STORAGE_BACKEND = "sqlite"
$env:ASEP_SQLITE_DATABASE = "storage/asep.db"
```

## Executar

CLI:

```powershell
asep --help
asep run projects/asep-self-development
```

Dashboard API local:

```powershell
python -m uvicorn asep.api.composition:create_default_app --factory --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/api/v1/health`.

## Validar

```powershell
python scripts/verify_environment.py
python -m pytest -v
python -m compileall src tests
git diff --check
```

Resultado esperado nesta fotografia: 625 testes aprovados.

## Problemas comuns

- `asep` não encontrado: ative `.venv` e reinstale com `-e ".[test]"`.
- PowerShell bloqueia ativação: use diretamente
  `.\.venv\Scripts\python.exe`.
- imports falham: confirme que a instalação editável foi executada.
- backend inválido: use `memory`, `file` ou `sqlite`, em minúsculas.
- SQLite não abre: confira caminho/permissão e não aponte para um diretório.
- testes temporários falham por permissão: confirme permissões de `%TEMP%`.

## Continuidade

Leia, nesta ordem:

1. [PROJECT_STATE](project/PROJECT_STATE.md);
2. [NEXT_STEPS](project/NEXT_STEPS.md);
3. [DocumentationIndex](docs/DocumentationIndex.md);
4. [MIGRATION_CHECKLIST](project/MIGRATION_CHECKLIST.md).
