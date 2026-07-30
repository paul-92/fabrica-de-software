# Mapa da arquitetura ASEP

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente na Sprint 7.5

## Visão Geral

Mapa em cinco níveis para localizar responsabilidades sem substituir a
[Architecture v1](ASEP-Architecture-v1.md).

## O Problema

Um único diagrama detalhado é difícil para iniciantes e insuficiente para
arquitetos que investigam dependências.

## A Solução

Apresentar alto nível, módulos, componentes, execução e dados.

## Explicação simples

A ASEP recebe comandos, coordena trabalho, guarda resultados e oferece
consultas. Cada andar conhece apenas os andares necessários.

## Explicação técnica

### 1. Visão de alto nível

```text
Entradas -> Aplicação -> Domínio/Execução -> Infraestrutura
                         |                    |
                         +---- Persistência --+
```

Entradas não implementam domínio; infraestrutura adapta processos e storage.

### 2. Visão por módulos

```text
cli/api
  |
  v
application/orchestrator ----> execution/workflow
  |                                  |
  v                                  v
configuration -> repositories     prompting/package/providers
                       |
          +------------+------------+
          v            v            v
        memory         file        sqlite
```

### 3. Visão por componentes de persistência

```text
Configuration -> ApplicationSettings -> RepositoryFactory
                                            |
                         +------------------+------------------+
                         v                                     v
               RunRepository                         TimelineRepository
               /      |      \                       /      |       \
          memory     file   sqlite               memory    file    sqlite
                              \                              /
                               +--> SQLiteDatabase <--------+
```

### 4. Fluxo de execução

```text
CLI run -> ExecutionBootstrap -> Orchestrator -> StageExecutionService
                                                   |
                              runtime ou prompt/package/provider
                                                   |
                                      artifacts + quality gate
```

### 5. Fluxo de dados de consulta

```text
asep.db -> SQLite repositories -> RunQueryService -> MetricsService
                                   |                    |
                                   +------> Dashboard API
                                   `------> History CLI
```

Cada diagrama reduz o nível de detalhe para uma pergunta diferente.

## Componentes envolvidos

CLI/API, application, execution, workflow, providers, artifacts, quality,
configuration, repositories, SQLite, Query, Metrics e exporters.

## Fluxo completo

Configuração escolhe infraestrutura; execução produz estado/artefatos;
repositories expõem Runs/Timeline; consultas projetam histórico e métricas.

## Dependências

Consumidores dependem de contratos. Providers não conhecem Orchestrator.
Exporters dependem de ExecutionGraph. Serviços não conhecem adapters SQLite.
Veja [Dependencies](../persistence/Dependencies.md).

## Exemplos

Trocar `memory` por `sqlite` altera `ApplicationSettings`, não
`RunQueryService`.

## Testes

Testes unitários por módulo, contratos compartilhados e integrações CLI/API
evidenciam os fluxos. Testes arquiteturais inspecionam imports/construções.

## Erros comuns

Interpretar seta como fluxo de dados quando ela representa dependência; assumir
que todos os componentes participam de todo comando.

## Limitações

O mapa não representa cada classe, estado ou divergência histórica. Consulte
documentos especializados.

## Evolução futura

Atualizar níveis afetados somente após mudanças implementadas.

## Referências

[Architecture v1](ASEP-Architecture-v1.md),
[SQLite Architecture](../persistence/SQLiteArchitecture.md) e
[Execution](Execution.md).

## Relacionado a

Sprint 7.5; Fase 07; ADR-016; módulos principais; testes; Roadmap; Glossário.
