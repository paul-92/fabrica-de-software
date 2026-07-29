# Standard: repository-structure

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Artefatos de projeto ficam em `projects/<id>`; globais aprovados em `artifacts/`; catálogo em `registry/`.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Cada seção tem README ou navegação canônica e evita cópias divergentes.

## Opção dependente do contexto

- Subpastas adicionais são permitidas quando ownership, retenção e finalidade estiverem documentados.

## Evidência obrigatória

- Evidência: árvore, links, ausência de pastas vazias e caminhos registrados existentes.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
