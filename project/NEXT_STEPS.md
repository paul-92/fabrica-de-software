# Próximos passos

**Estado:** Fase 23 em andamento; Sprint 23.4 pronta para fechamento intencional

**Atualizado em:** 2026-08-11

**Dono:** Engenharia ASEP

## Objetivo imediato

Registrar o fechamento intencional da Sprint 23.4 e priorizar explicitamente o
próximo incremento da Fase 23, sem assumir que 23.5 já foi aprovado.

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

## Continuidade da Fase 23

As Sprints 23.1–23.4 entregaram agentes operacionais e a projeção detalhada de
Quality Gates sequenciais. Produto deve decidir o escopo seguinte. Busca e
paginação, branding dinâmico, migração de YAML histórico e integração com
Intelligent Orchestration continuam candidatos, não requisitos aprovados.

Antes de qualquer novo slice, preservar as identidades distintas de `Run`,
`SequentialExecution` e `ProjectExecution`, a composição opt-in e as fronteiras
registradas no [ADR-033](../docs/adr/ADR-033-sequential-quality-boundary.md).

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
