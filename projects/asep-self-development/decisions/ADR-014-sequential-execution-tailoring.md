# ADR-014 — Tailoring sequencial executável do projeto piloto

**Status:** accepted  
**Responsável:** Software Architect  
**Data:** 2026-07-28

## Contexto

O workflow corporativo `software-project` contém grupos paralelos e uma etapa
condicional. A Sprint 2 proíbe executar, adaptar silenciosamente ou avaliar essas
características. Somente o Business Analyst possui adaptador executável.

## Problema

Permitir uma demonstração ponta a ponta determinística sem alterar o workflow
corporativo nem fingir suporte aos demais agentes.

## Alternativas

1. modificar `software-project`;
2. linearizar seus grupos implicitamente;
3. criar um tailoring versionado e explícito para o piloto;
4. bloquear toda a Sprint até existirem todos os agentes.

## Decisão

Criar `asep-self-development-sequential` versão `0.1.0`, com uma única etapa de
Business Analysis, um único agente e `QG-ANALYSIS`. O motor continua rejeitando
qualquer workflow com modo `parallel` ou `conditional`.

## Justificativa

A alternativa preserva a fonte corporativa, torna a limitação observável e
entrega o menor fluxo executável compatível com o escopo aprovado.

## Consequências

- o projeto piloto usa o tailoring durante a Sprint 2;
- o workflow corporativo permanece inalterado e não executável pelo motor atual;
- novos agentes ou etapas exigem versão nova e aprovação;
- este tailoring não representa o lifecycle completo da ASEP.

## Riscos

O fluxo de uma etapa pode dar falsa impressão de engine completa. CLI, relatórios
e logs devem explicitar a limitação; testes de rejeição preservam o fail-closed.
