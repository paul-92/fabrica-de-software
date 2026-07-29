# Standard: versioning

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Componentes registráveis usam SemVer; projeto fixa a versão executada; breaking change incrementa major.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Manter changelog, janela de depreciação e compatibilidade retroativa quando viável.

## Opção dependente do contexto

- Artefatos internos podem usar versão documental incremental se não forem consumidos como contrato.

## Evidência obrigatória

- Evidência: versão, diff, análise de compatibilidade, migração e aprovação do dono.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
