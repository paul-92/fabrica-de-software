# Standard: adr

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- ADR contém contexto, problema, alternativas, decisão, justificativa, consequências, riscos, responsáveis, data e status.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Não reescrever decisão aceita; criar sucessor e ligar `supersedes/superseded-by`.

## Opção dependente do contexto

- ADR é obrigatório para decisão material, difícil de reverter, transversal ou que cria exceção.

## Evidência obrigatória

- Evidência: aprovação do dono técnico e consultados, links aos requisitos e plano de saída.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
