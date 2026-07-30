# Auditoria de dependências — RC1

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída em 2026-07-30

## Modelo

O projeto usa `pip`, `venv`, setuptools e `pyproject.toml`, com Python `>=3.12`.
Não há lockfile. `pip check` não encontrou dependências quebradas.

## Dependências diretas

| Pacote | Uso comprovado |
|---|---|
| Typer/Rich | CLI |
| Pydantic | contratos e validação |
| PyYAML | loaders, estado e pacotes |
| Jinja2 | Business Analyst determinístico |
| FastAPI | Dashboard API |
| Uvicorn | servidor operacional documentado |
| pytest/pytest-cov | testes e cobertura |
| HTTPX | `TestClient` de API |

## Correção

O extra de testes declarava `httpx2`, enquanto os testes e o `TestClient`
dependem de `httpx`. Foi corrigido para `httpx>=0.28,<1`. São projetos
distintos; manter `httpx2` tornaria uma instalação limpa não reproduzível.

## Ambiente observado

Typer 0.27.0, Pydantic 2.13.4, PyYAML 6.0.3, Rich 14.3.4, Jinja2 3.1.6,
FastAPI 0.141.1, Uvicorn 0.52.0, pytest 8.4.2, pytest-cov 7.1.0 e HTTPX
0.28.1.

## Riscos e pendências

- intervalos sem lock podem resolver versões diferentes;
- fixar versões agora sem CI multiplataforma seria arriscado;
- criar lockfile deve ser uma decisão explícita antes de release estável;
- nenhuma biblioteca foi atualizada no RC1.

