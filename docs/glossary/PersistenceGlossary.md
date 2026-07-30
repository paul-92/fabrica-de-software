# Glossário de persistência e execução

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Visão Geral

Termos necessários para compreender a Fase 07 e a Sprint 7.5.

## O Problema

Palavras técnicas sem definição criam interpretações incompatíveis.

## A Solução

Cada entrada informa significado, analogia simples, definição técnica e uso na
ASEP.

## Explicação simples

Este é o dicionário da arquitetura.

## Explicação técnica

| Termo | Significado e explicação simples | Explicação técnica | Uso na ASEP |
|---|---|---|---|
| Run | Uma execução completa | Snapshot imutável de status, timestamps e contexto | `RunRepository` |
| Timeline | Diário do que aconteceu | Sequência de `TimelineEvent` ordenada | auditoria por `run_id` |
| Repository | Gaveta de dados | Porta que abstrai persistência | Run/Timeline protocols |
| Factory | Responsável por escolher a gaveta | Objeto que constrói implementações por configuração | `RepositoryFactory` |
| Configuration | Painel de opções | Loader de defaults/ambiente | `Configuration.load()` |
| ApplicationSettings | Fotografia do painel | Dataclass imutável e validada | entrada da Factory |
| Interface/Protocol | Forma combinada de conversar | Contrato estrutural de métodos | portas dos repositories |
| Persistência | Fazer o dado sobreviver | Armazenamento além da memória do processo | file e sqlite |
| SQLite | Caderno local em tabelas | Banco relacional embutido em um arquivo | `storage/asep.db` |
| Schema | Planta do banco | Tabelas, colunas, chaves e índices | `SQLiteDatabase._SCHEMA` |
| Tabela | Seção do caderno | Conjunto de linhas com colunas | `runs`, `timeline_events` |
| Chave primária | Código único | Constraint que impede IDs duplicados | `id` |
| Índice | Índice remissivo | Estrutura para acelerar busca | eventos por `run_id` |
| Payload | Envelope de detalhes | JSON canônico completo | coluna `payload` |
| Codec | Tradutor | encode/decode entre modelo e dados JSON | Run/Event codecs |
| Upsert | Inserir ou atualizar | `INSERT ... ON CONFLICT DO UPDATE` | salvar Run |
| Append-only | Diário sem reescrita | Operação que só aceita novo ID | Timeline |
| Transação | Operação tudo-ou-nada | commit em sucesso, rollback em falha | conexão SQLite |
| DTO | Pacote de transporte de dados | Data Transfer Object sem regra de persistência | contratos tipados quando aplicável |
| Entity | Objeto com identidade | Conceito identificado ao longo do tempo | Run/evento por ID |
| Use Case | Objetivo executado pela aplicação | Coordenação de portas e domínio | consultas/execução |
| Service | Componente de coordenação | Implementa caso de uso sem detalhe de adapter | Query/Metrics |
| Provider | Especialista executor | Porta/adaptador para execução externa | fluxo de agentes |
| Workflow | Roteiro de etapas | Definição validada pelo engine | execução ASEP |
| Dashboard | Painel de acompanhamento | API/projeção somente leitura | consulta Runs/métricas |

## Componentes envolvidos

Domínio, aplicação, configuração, repositories, SQLite e apresentação.

## Fluxo completo

```text
termo -> conceito simples -> definição técnica -> localização no código
```

## Dependências

As definições dependem do código atual e do glossário legado
[`docs/glossary.md`](../glossary.md), que permanece preservado.

## Exemplos

“A Factory leu ApplicationSettings e entregou um Repository SQLite que fez
upsert do Run em uma transação.”

## Testes

Termos são confrontados com nomes públicos, schema e testes existentes.

## Erros comuns

Repository não é banco; ele é a abstração. SQLite não é servidor. Timeline não
é log textual: é um contrato estruturado.

## Limitações

O glossário cobre termos relevantes à Sprint; não substitui documentação de
cada domínio.

## Evolução futura

Adicionar termos somente quando existirem no produto, preservando definições
históricas quando mudarem.

## Referências

[Sprint 7.5](../phase-07/Sprint-7.5-SQLite-Repository.md) e
[arquitetura](../persistence/SQLiteArchitecture.md).

## Relacionado a

Fase 07; ADR-016; componentes de persistência; testes; Roadmap; Architecture.
