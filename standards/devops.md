# Standard: devops

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Ambientes são reproduzíveis; deploy é observável e reversível; segredos nunca ficam no repositório.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Automatizar checks, separação de funções, backup/restauração e rollout progressivo.

## Opção dependente do contexto

- Plataforma e topologia dependem de SLO, capacidade, risco, equipe e custo total.

## Evidência obrigatória

- Evidência: pipeline, plano de deploy, rollback exercitado, runbook e go/no-go.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
