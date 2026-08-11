# Fase 22 — White-label Presentation Layer / Graphical Interface

**Público:** produto, engenharia, arquitetura, qualidade e operações

**Dono:** Engenharia ASEP

**Versão:** 1.0

**Status:** implementação funcional concluída; gate consolidado final pendente

## Objetivo e fronteira

Disponibilizar uma camada visual operacional e white-label que consuma somente
contratos públicos versionados conforme o fluxo:

```text
Presentation → Application/API → Application Services → Domain/Core
```

A apresentação não acessa Core, repositories, Agent Runtime, registries
internos, persistence, Planning Engine, Quality Gate Engine ou módulos Python
internos.

## Entregas implementadas

- fundação Next.js, App Shell responsivo, navegação, tokens, temas e componentes;
- Dashboard com métricas, providers, runs recentes e estados operacionais;
- Projetos com criação, seleção, workspace seguro, arquivos, sessões, histórico
  e execução controlada por runtime de IA;
- continuidade por sessão, memória persistente, context budgeting determinístico
  e exploração read-only de memória;
- Executions com listagem, detalhe, timeline, status e evidências;
- Planning/Intelligent Engineering pela Application/API;
- Quality com projeções públicas agregadas de runs, status e providers;
- Knowledge no percurso Projeto → Sessão → Memórias;
- Agents pela projeção declarativa `GET /api/v1/agents`;
- branding de deployment por `NEXT_PUBLIC_*` e preferência local de tema.

## Contrato público de Agents

`GET /api/v1/agents` expõe exclusivamente `agent_id`, `name`, `version`,
`lifecycle_status`, `department` e `capabilities`. `lifecycle_status` é
declarativo e não comprova disponibilidade do runtime.

## White-label

A configuração suporta nome do produto, nome curto, logo, favicon, cores
primária e secundária, tema padrão, texto da área de trabalho e texto
institucional da sidebar. Personalização administrativa em runtime e
persistência server-side das preferências estão fora do contrato desta fase.

## Hardening realizado

Em 2026-08-11 foram verificados:

- ausência de imports do frontend para pacotes Python ou módulos internos;
- centralização das chamadas remotas no cliente HTTP e nos services;
- uso de rotas públicas versionadas sob `/api/v1`;
- timeout HTTP e separação dos tipos de erro;
- ausência de `TODO`, `FIXME`, `HACK` e placeholders silenciosos no frontend.

Nenhum defeito de código comprovado foi encontrado. Alterações especulativas
foram evitadas enquanto o gate executável permanece indisponível.

## Evidências e gate consolidado

Durante o desenvolvimento da Presentation Layer, os gates frontend foram
executados em ambiente com Node/npm disponível. Typecheck, lint e build Next.js
foram aprovados.

A última falha identificada estava restrita ao isolamento entre testes de
`ThemeToggle.test.tsx`. Após a correção, os 3 testes focados desse componente
passaram.

Em 2026-08-11 também foram aprovados 11 testes focados dos contratos
Application/API de Agents e a inspeção estática não encontrou imports do
frontend para módulos Python internos.

| Verificação | Evidência |
| --- | --- |
| Fronteira estática do frontend | passou |
| Contratos Application/API de Agents | `11 passed` |
| Typecheck durante o desenvolvimento | passou |
| Lint durante o desenvolvimento | passou |
| Build Next.js durante o desenvolvimento | passou |
| `ThemeToggle.test.tsx` após correção final | `3 passed` |
| Gate frontend consolidado sobre o estado final | pendente |

O fechamento formal exige uma nova execução consolidada de:

```text
npm test
npm run typecheck
npm run lint
npm run build
## Limitações conhecidas

- branding dinâmico por API ainda não existe;
- preferências visuais não possuem persistência server-side;
- Agents não expõe runtime health ou métricas por agente;
- Quality não expõe critérios detalhados dos Quality Gates;
- Knowledge não possui busca, paginação ou agregação global;
- runtime e workflows preservam as limitações das fases anteriores.

## Próxima fase proposta

Propõe-se que Produto avalie uma Fase 23 de operacionalização e projeções
públicas. Branding administrável, observabilidade pública de agentes, projeção
detalhada de Quality Gates e evolução das consultas de Knowledge são
candidatos, não requisitos aprovados. Produto prioriza; Arquitetura versiona os
contratos; Qualidade define os critérios de aceite.

## Checklist de fechamento

- [x] objetivo, público, dono, versão, status e fronteira documentados;
- [x] entregas e limitações sincronizadas;
- [x] hardening estático e testes focados de Agents executados;
- [x] proposta de continuidade registrada sem aprovação implícita;
- [ ] `npm test` aprovado;
- [ ] `npm run typecheck` aprovado;
- [ ] `npm run lint` aprovado;
- [ ] `npm run build` aprovado;
- [ ] aceite formal do gate por Qualidade;
- [ ] priorização da próxima fase por Produto.

## Retomada e responsabilidade

Engenharia deve executar os quatro gates em ambiente compatível com Node/npm ou
CI equivalente e rastreável ao mesmo commit. Qualidade avalia as evidências e decide o gate. Produto decide o
próximo escopo quando houver prioridade explícita.
