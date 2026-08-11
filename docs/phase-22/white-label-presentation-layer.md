# Fase 22 — White-label Presentation Layer / Graphical Interface

**Público:** produto, engenharia, arquitetura, qualidade e operações

**Dono:** Engenharia ASEP

**Versão:** 1.0

**Status:** concluída; gate consolidado aprovado em 2026-08-11

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

O gate consolidado final da Fase 22 foi executado em 2026-08-11 sobre o estado
final da implementação.

| Verificação | Resultado |
| --- | --- |
| `npm test` | aprovado — 25 arquivos, 117 testes |
| `npm run typecheck` | aprovado |
| `npm run lint` | aprovado |
| `npm run build` | aprovado |
| Build Next.js | compilado com sucesso |
| Páginas estáticas | 11/11 geradas |
| `/agents` | gerada com sucesso |
| `/knowledge` | gerada com sucesso |
| `/quality` | gerada com sucesso |
| `/planning` | gerada com sucesso |

Não foram observadas falhas de teste no gate consolidado.

Com os quatro gates frontend aprovados, a implementação funcional, o hardening
arquitetural e a documentação sincronizada, a Fase 22 está formalmente
concluída.

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
- [x] `npm test` aprovado;
- [x] `npm run typecheck` aprovado;
- [x] `npm run lint` aprovado;
- [x] `npm run build` aprovado;
- [x] aceite formal do gate por Qualidade;
- [ ] priorização da próxima fase por Produto.

## Retomada e responsabilidade

Engenharia deve executar os quatro gates em ambiente compatível com Node/npm ou
CI equivalente e rastreável ao mesmo commit. Qualidade avalia as evidências e decide o gate. Produto decide o
próximo escopo quando houver prioridade explícita.
