# Standard: api

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Contrato explicita autenticação, autorização, erros, idempotência, paginação, limites e versionamento.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Validar compatibilidade do consumidor, correlation ID, observabilidade e política de depreciação.

## Opção dependente do contexto

- REST, GraphQL, RPC ou eventos dependem de semântica, consumidores, latência e evolução.

## Evidência obrigatória

- Evidência: contrato validado, testes de contrato, casos de abuso e exemplos mínimos executáveis.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
