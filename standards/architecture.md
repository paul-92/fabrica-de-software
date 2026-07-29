# Standard: architecture

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Documentar contexto, atributos de qualidade, fronteiras, dados, dependências, falhas e operação.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Comparar alternativas e favorecer modularidade, reversibilidade e evolução baseada em evidência.

## Opção dependente do contexto

- Estilo arquitetural e tecnologia dependem de escala, equipe, risco e restrições confirmadas.

## Evidência obrigatória

- Evidência: documento, diagramas necessários, ADRs, threat model e revisão multidisciplinar.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
