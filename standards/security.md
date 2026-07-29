# Standard: security

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Aplicar menor privilégio, deny-by-default, proteção de segredos, classificação e validação de entrada.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Modelar ameaças, testar autorização e supply chain, definir retenção e resposta a incidentes.

## Opção dependente do contexto

- Controles concretos dependem de dados, exposição, ameaças e obrigações aplicáveis.

## Evidência obrigatória

- Evidência: threat model, achados priorizados, verificação de controles e aceite autorizado.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
