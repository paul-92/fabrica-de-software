# Inventário de ambiente da ASEP

**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** fotografia não sensível de 2026-07-30

## Plataforma validada

- sistema: Windows 11;
- arquitetura: AMD64, Python 64-bit;
- runtime observado: CPython 3.14.4;
- runtime suportado pelo pacote: Python `>=3.12`;
- suporte pretendido pelo código: Windows, Linux e macOS;
- validação completa desta fotografia: somente Windows.

## Dependências e ferramentas

- gerenciamento: `pip`, `venv`, setuptools e `pyproject.toml`;
- instalação: `python -m pip install -e ".[test]"`;
- não existe lockfile; os intervalos do `pyproject.toml` são o contrato atual;
- Git é necessário;
- Codex CLI é necessário apenas para usar o `CodexProvider` real;
- cliente `sqlite3` é opcional para inspeção e backup;
- SQLite usado pela aplicação vem da biblioteca padrão `sqlite3`;
- não há ORM, serviço de banco ou dependência nativa obrigatória conhecida.

Dependências de runtime registradas: Typer, Pydantic, PyYAML, Rich, Jinja2,
FastAPI e Uvicorn. Dependências de teste: pytest, pytest-cov e HTTPX. As versões
resolvidas na máquina antiga são evidência do ambiente, não um lock reproduzível.

## Configuração

| Variável | Default | Uso |
|---|---|---|
| `ASEP_STORAGE_BACKEND` | `memory` | `memory`, `file` ou `sqlite` |
| `ASEP_STORAGE_DIRECTORY` | `storage` | raiz do backend file |
| `ASEP_RUNS_FILENAME` | `runs.json` | arquivo de Runs |
| `ASEP_TIMELINE_FILENAME` | `timeline-events.json` | arquivo da Timeline |
| `ASEP_WORKFLOWS_FILENAME` | `workflow-snapshots.json` | snapshots de workflow |
| `ASEP_SQLITE_DATABASE` | `storage/asep.db` | banco SQLite |

O arquivo `.env.example` contém exemplos seguros. A aplicação consulta o
ambiente do processo e não faz carregamento automático de `.env`.

## Execução e validação

```text
asep --help
asep run projects/asep-self-development
python -m uvicorn asep.api.composition:create_default_app --factory --host 127.0.0.1 --port 8000
python scripts/verify_environment.py
python -m pytest -v
python -m compileall src tests
```

A Dashboard API usa a porta local `8000` no comando documentado.

## Dados locais

- SQLite padrão: `storage/asep.db`, criado automaticamente quando o backend
  SQLite é usado;
- backend file: diretório configurado por `ASEP_STORAGE_DIRECTORY`;
- execução do projeto: `.asep/`, `artifacts/runs/` e `logs/runs/` sob o projeto;
- temporários de testes: diretório temporário do pytest;
- nenhum arquivo SQLite foi encontrado no workspace nesta fotografia.

Os diretórios de execução encontrados são ignorados pelo Git e precisam de
backup separado caso devam acompanhar a migração.

## Problemas conhecidos

- sem lockfile, uma instalação futura pode resolver versões diferentes;
- paths temporários profundos no Windows exigem nomes temporários curtos;
- antivírus, permissões de `%TEMP%` e arquivos SQLite abertos podem interferir;
- paths e ativação de ambiente virtual diferem entre PowerShell e shells Unix;
- backend padrão `memory` não preserva dados ao encerrar o processo.

## Segurança

Não registrar neste documento senhas, tokens, chaves, cookies, dados pessoais
ou URLs privadas. A inspeção por padrões em arquivos rastreados não indicou
segredos em configuração/código, mas não substitui scanner de todo o histórico
Git nem revisão humana antes da migração.
