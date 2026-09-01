# ADR-034 — Provisioning controlado de dependências aprovadas

**Status:** aceito por decisão humana em 2026-08-29 | **Versão:** 1.0

## Contexto

Project Engineering produzia manifests em hosted projects, mas os validators
pressupunham dependências previamente materializadas. O caminho executado pelo
DeveloperAgent não atravessava `_invoke_runtime`, único ponto que aquecia caches,
e o cache não criava `node_modules` nem lockfile.

## Decisão

Entre a captura de changes e a validação, a ASEP materializa dependências Node
somente quando existe um `dependency_plan` integralmente aprovado. Todos os
manifests do monorepo são comparados com pares package/versão aprovados; packages
internos precisam apontar para a versão exata do package local. Divergência,
pacote externo adicional, versão ausente ou falha do package manager bloqueiam a
execução antes dos validators.

Sem lockfile, a ASEP executa `npm install --package-lock-only` com versões exatas;
depois executa `npm ci`. Scripts, audit, funding, update, global install, `latest`
e `--force` não fazem parte do contrato. Registry e cache permanecem confinados.

Cada resultado persiste evidence sem conteúdo de arquivos, com fingerprints do
dependency plan e dos manifests. Evidence compatível mais lockfile e
`node_modules` permite reutilização sem reinstall; qualquer incompatibilidade
força novo provisioning.

## Consequências e rollback

Validators passam a depender de evidence válida e nunca antecedem provisioning.
O custo de rede/disco ocorre somente quando necessário. O rollback consiste em
remover a chamada de materialização da fronteira de Project Engineering; dados e
histórico de evidence permanecem compatíveis porque os novos campos são opcionais.

## Evidência

- `src/asep/dependency_provisioning.py`
- `src/asep/application/project_ai_runtime.py`
- `src/asep/application/project_engineering_execution.py`
- `tests/qa/application/test_controlled_dependency_materialization.py`
