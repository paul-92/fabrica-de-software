# Standard: naming

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- IDs e arquivos usam `kebab-case`; datas usam `YYYY-MM-DD`; IDs publicados não são reutilizados.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Nomear pelo conceito de domínio, evitando abreviações locais e nomes de implementação.

## Opção dependente do contexto

- Convenções externas podem prevalecer em APIs, linguagens e plataformas, desde que documentadas.

## Evidência obrigatória

- Evidência: lint ou revisão de nomes, glossário e mapa de renomeação quando houver quebra.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
