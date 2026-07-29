# Standard: ai

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Definir finalidade, limites, dados autorizados, avaliação, supervisão, fallback e comunicação de incerteza.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Versionar modelo/prompt/dataset, testar abuso, drift, vieses relevantes e falhas previsíveis.

## Opção dependente do contexto

- Modelo, RAG, fine-tuning ou regra determinística dependem de valor, risco, dados e custo.

## Evidência obrigatória

- Evidência: evaluation plan, model card, conjunto versionado, resultados e aceite de risco.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
