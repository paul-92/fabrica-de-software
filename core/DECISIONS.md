# Decisões e ADR

**Dono:** Tech Lead para ADRs; dono do domínio para demais decisões  
**Status:** ativo | **Versão:** 0.1.1

## Quando registrar

Decisão difícil de reverter, transversal, cara, que altera contrato/standard,
introduz tecnologia, aceita risco ou cria exceção exige registro formal. Decisão
local e reversível pode ficar no artefato do domínio, desde que tenha dono e fonte.

## Estrutura obrigatória

ID e título; contexto; problema; alternativas; decisão; justificativa;
consequências positivas e negativas; riscos; responsáveis; consultados; data;
status (`proposed`, `accepted`, `rejected`, `superseded`, `deprecated`) e links.

## Lifecycle

Uma proposta recebe revisores afetados e autoridade definida em
[ORGANIZATION.md](ORGANIZATION.md). Depois de aceita, não é reescrita para parecer
que sempre esteve correta. Mudança cria decisão sucessora com `supersedes` e o
registro anterior recebe `superseded-by`.

## Evidência e auditoria

A justificativa referencia requisitos, restrições, experimentos ou dados reais.
Ausência de evidência é declarada como hipótese. Exceções incluem validade e plano
de remoção. Auditoria verifica autoridade, alternativas relevantes e consequências.

Template: [templates/architecture/adr.md](../templates/architecture/adr.md).
