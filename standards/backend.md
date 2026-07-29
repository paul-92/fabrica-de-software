# Standard: backend

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Serviços validam entrada e autorização no servidor, preservam idempotência e emitem telemetria segura.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Separar domínio de infraestrutura, limitar transações e tratar timeout, retry e falha parcial.

## Opção dependente do contexto

- Estrutura interna e estilo de serviço dependem da arquitetura aprovada.

## Evidência obrigatória

- Evidência: revisão, análise estática, testes de unidade/integração/contrato e rastreabilidade.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
