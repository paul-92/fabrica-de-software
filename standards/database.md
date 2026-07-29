# Standard: database

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Definir fonte de verdade, ownership, classificação, integridade, migrações, retenção, backup e restauração.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Modelar por padrões de acesso confirmados e testar migração/rollback com volume representativo.

## Opção dependente do contexto

- Modelo relacional, documento, chave-valor ou analítico depende de consistência, consulta e operação.

## Evidência obrigatória

- Evidência: modelo, dicionário, plano de migração, teste de restauração e controles de acesso.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
