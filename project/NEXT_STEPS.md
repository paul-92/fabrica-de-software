# Próximos passos

**Estado:** Fase 22 funcionalmente concluída; fechamento formal pendente

**Atualizado em:** 2026-08-11

**Dono:** Engenharia ASEP

## Objetivo imediato

Concluir o gate consolidado da White-label Presentation Layer e entregar as
evidências para decisão de Qualidade.

## Gate pendente

O fechamento formal exige uma execução consolidada dos gates frontend após a
última correção realizada em `ThemeToggle.test.tsx`.

Em ambiente com Node/npm compatível com o projeto, executar em `frontend/`:

```text
npm test
npm run typecheck
npm run lint
npm run build.

## Evidências já disponíveis

- inspeção estática sem imports do frontend para módulos Python internos;
- chamadas remotas centralizadas nos contratos HTTP públicos `/api/v1`;
- 11 testes focados de Application/API para Agents aprovados;
- documentação, estado e roadmap sincronizados com a Fase 22;
- checklist detalhado em
  [Fase 22](../docs/phase-22/white-label-presentation-layer.md).

## Critérios de retomada e fechamento

1. Executar os quatro gates em ambiente compatível com Node/npm ou CI equivalente..
2. Falhas, se houver, são classificadas e corrigidas com novas evidências.
3. Qualidade avalia os resultados e decide o gate final.
4. O estado da fase só muda para formalmente encerrada após essa decisão.

## Próxima fase proposta

Produto deve decidir se abre uma Fase 23 de operacionalização e projeções
públicas. Branding administrável, health/métricas de agentes, detalhamento de
Quality Gates e consultas avançadas de Knowledge são candidatos derivados das
limitações atuais, não escopo aprovado.

## Riscos e preservação

- o worktree contém milhares de remoções preexistentes em
  `.pytest-tmp-sprint91-*`; não restaurar nem incluir essas mudanças sem decisão
  explícita;
- `frontend/next-env.d.ts` já estava modificado antes deste fechamento;
- publicação, commit, push, CI remoto e instalação de ferramentas exigem ação
  ou autorização própria;
- Python 3.11.9 no ambiente atual está abaixo do mínimo documental `>=3.12`,
  embora os testes focados executados tenham passado.

## Responsáveis e gatilhos

- **Engenharia:** ambiente Node/npm e execução do gate;
- **Qualidade:** aceite ou reprovação com achados;
- **Produto:** priorização da próxima fase;
- **Gatilho:** disponibilidade do ambiente de frontend ou resultado de CI
  equivalente, rastreável ao mesmo commit.
