# Standard: testing

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Testes cobrem critérios e riscos; resultados registram ambiente, versão, dados, execução e defeitos.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Priorizar feedback rápido: unidade para lógica, integração para fronteiras e E2E para jornadas críticas.

## Opção dependente do contexto

- Níveis, automação e testes não funcionais dependem de risco e arquitetura.

## Evidência obrigatória

- Evidência: estratégia, matriz de cobertura de risco, relatório reproduzível e risco residual.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
