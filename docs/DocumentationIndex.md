# Índice da documentação ASEP

**Público:** todas as pessoas que trabalham com a ASEP  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Visão Geral

Ponto de entrada para a documentação. O código é a fonte da verdade;
documentos explicam estado atual, decisões e história.

## O Problema

Arquivos sem mapa dificultam descobrir por onde começar e qual documento é
canônico.

## A Solução

Organizar por objetivo e fornecer público, descrição e referências cruzadas.

## Explicação simples

Este índice é o catálogo de uma biblioteca.

## Explicação técnica

### Estrutura

```text
docs/
|-- README.md
|-- DocumentationIndex.md
|-- architecture/       estado atual e mapas
|-- persistence/        implementação de storage
|-- phase-07/           fotografia da Sprint
|-- history/            narrativa de evolução
|-- adr/                decisões novas
|-- glossary/           termos por domínio
|-- architecture/decisions/  ADRs legados preservados
`-- *.md                documentos históricos/de apoio
```

### Trilhas recomendadas

| Público/objetivo | Comece por | Continue em |
|---|---|---|
| Iniciante | [README](README.md) | [Glossário](glossary/PersistenceGlossary.md) |
| Entender a Sprint 7.5 | [fotografia](phase-07/Sprint-7.5-SQLite-Repository.md) | [repositórios](persistence/SQLiteRepositories.md) |
| Arquitetura rápida | [Architecture Map](architecture/ArchitectureMap.md) | [Architecture v1](architecture/ASEP-Architecture-v1.md) |
| Implementar/manter SQLite | [SQLite Architecture](persistence/SQLiteArchitecture.md) | [Schema](persistence/DatabaseSchema.md) |
| Operar/configurar | [SQLite Configuration](persistence/SQLiteConfiguration.md) | [Troubleshooting dos repositories](persistence/SQLiteRepositories.md#possíveis-erros) |
| Compreender decisões | [ADR-016](adr/ADR-016-sqlite-persistence.md) | [Dependencies](persistence/Dependencies.md) |
| Compreender evolução | [History](history/HistoryOfASEP.md) | [Phase 07](history/Phase-07.md) |

### Catálogo de arquitetura

- [ASEP-Architecture-v1](architecture/ASEP-Architecture-v1.md): referência
  executável geral; público técnico.
- [ArchitectureMap](architecture/ArchitectureMap.md): cinco níveis de visão;
  iniciantes e arquitetos.
- [Core Domain](architecture/Core-Domain.md): fronteiras centrais.
- [Execution](architecture/Execution.md): lifecycle de execução.
- [ExecutionPackage](architecture/ExecutionPackage.md): pacote de provider.
- [ExecutionGraph](architecture/ExecutionGraph.md): representação canônica.
- [Providers](architecture/Providers.md): adapters de agentes externos.
- [Exporters](architecture/Exporters.md): Mermaid/BPMN/JSON.
- [CLI](architecture/CLI.md): comandos e códigos de saída.
- [RunRepository](architecture/RunRepository.md): porta e backends de Run.
- [ExecutionTimeline](architecture/ExecutionTimeline.md): eventos/repositories.
- [RunQueryService](architecture/RunQueryService.md): consultas.
- [MetricsService](architecture/MetricsService.md): métricas.
- [DashboardAPI](architecture/DashboardAPI.md): API somente leitura.
- [Roadmap](architecture/Roadmap.md): entregas e próximos marcos.

### Catálogo da Sprint 7.5

- [Sprint 7.5](phase-07/Sprint-7.5-SQLite-Repository.md): fotografia e
  rastreabilidade.
- [SQLiteRepositories](persistence/SQLiteRepositories.md): tutorial completo.
- [DatabaseSchema](persistence/DatabaseSchema.md): schema real.
- [SQLiteArchitecture](persistence/SQLiteArchitecture.md): camadas e fluxos.
- [SQLiteConfiguration](persistence/SQLiteConfiguration.md): ambiente/defaults.
- [Dependencies](persistence/Dependencies.md): dependências permitidas.
- [ADR-016](adr/ADR-016-sqlite-persistence.md): decisão arquitetural.
- [Phase-07](history/Phase-07.md): evolução da fase.
- [HistoryOfASEP](history/HistoryOfASEP.md): narrativa da plataforma.
- [PersistenceGlossary](glossary/PersistenceGlossary.md): termos.

### Documentos preservados

O [glossário legado](glossary.md), governança, métricas e catálogo continuam
acessíveis. ADRs anteriores permanecem em
[`architecture/decisions`](architecture/decisions/ADR-001-core-domain-boundaries.md);
novos ADRs documentais usam `docs/adr/` até decisão de consolidação.

## Componentes envolvidos

Toda a documentação e os módulos que ela descreve.

## Fluxo completo

Pergunta -> trilha -> visão geral -> detalhe técnico -> ADR/história -> testes.

## Dependências

Links relativos; código/testes como evidência; `core/` prevalece em governança.

## Exemplos

Para diagnosticar schema: índice -> Sprint 7.5 -> DatabaseSchema -> testes
SQLite.

## Testes

Validação automática local verifica links, seções, placeholders e
`git diff --check`.

## Erros comuns

Usar roadmap como descrição do código; tratar ADR em review como decisão
aceita; ignorar status/versão.

## Limitações

Alguns documentos históricos anteriores não seguem o template atual; foram
preservados para não apagar contexto.

## Evolução futura

Adicionar trilhas somente junto de capacidades implementadas e atualizar este
índice em toda Sprint documental.

## Referências

[README](README.md), [Architecture v1](architecture/ASEP-Architecture-v1.md) e
[Roadmap](architecture/Roadmap.md).

## Relacionado a

Sprint 7.5; Fase 07; ADRs; componentes; testes; arquitetura; glossários.
