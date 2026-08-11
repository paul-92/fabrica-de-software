# Próximos passos

**Estado:** Fase 22 formalmente concluída

**Atualizado em:** 2026-08-11

**Dono:** Engenharia ASEP

## Objetivo imediato

Definir e priorizar o próximo incremento da ASEP após a conclusão da
White-label Presentation Layer.

## Gate final da Fase 22

O gate frontend consolidado foi aprovado em 2026-08-11:

- `npm test`: aprovado — 25 arquivos e 117 testes;
- `npm run typecheck`: aprovado;
- `npm run lint`: aprovado;
- `npm run build`: aprovado;
- build Next.js concluído com sucesso;
- 11 páginas estáticas geradas;
- `/agents`, `/knowledge`, `/quality` e `/planning` confirmadas no build.

A Fase 22 não possui gate frontend pendente.

## Evidências de fechamento

- inspeção estática sem imports do frontend para módulos Python internos;
- chamadas remotas centralizadas nos contratos HTTP públicos `/api/v1`;
- 11 testes focados de Application/API para Agents aprovados;
- 25 arquivos de testes frontend e 117 testes aprovados no gate consolidado;
- typecheck aprovado;
- lint aprovado;
- build de produção Next.js aprovado;
- documentação, estado e roadmap sincronizados com a Fase 22;
- checklist detalhado em
  [Fase 22](../docs/phase-22/white-label-presentation-layer.md).

## Próxima fase proposta

Produto deve definir e priorizar o próximo incremento da plataforma.

Uma possível Fase 23 de operacionalização e projeções públicas pode considerar:

- branding administrável em runtime;
- health e métricas públicas por agente;
- detalhamento público de Quality Gates;
- busca, paginação e consultas avançadas de Knowledge;
- evolução das capacidades operacionais expostas pela Presentation Layer.

Esses itens são candidatos derivados das limitações atuais e não constituem
escopo aprovado até que a próxima fase seja formalmente definida.

## Riscos e preservação

- alterações preexistentes fora do escopo não devem ser restauradas ou
  incluídas em commits sem decisão explícita;
- publicação, CI remoto e mudanças de infraestrutura permanecem atividades
  operacionais independentes;
- Python abaixo do mínimo documental `>=3.12`, caso presente em algum ambiente
  de desenvolvimento, deve ser tratado como limitação desse ambiente e não
  como alteração dos requisitos da plataforma.

## Responsabilidades para continuidade

- **Produto:** priorizar o próximo incremento;
- **Arquitetura:** avaliar os contratos públicos necessários;
- **Engenharia:** implementar somente o escopo aprovado;
- **Qualidade:** definir e validar os critérios de aceite da próxima fase.

## Gatilho de continuidade

A próxima fase deve começar somente após definição explícita de objetivo,
escopo, contratos necessários e critérios de aceite.