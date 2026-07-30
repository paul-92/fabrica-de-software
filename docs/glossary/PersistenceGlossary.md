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
| Workflow Orchestrator | Maestro de um roteiro | Serviço sequencial que coordena Steps e projeta lifecycle | `asep.workflow` |
| Workflow Step | Uma tarefa do roteiro | Protocol síncrono `execute(context)` | unidade simulável |
| Workflow Context | Mochila compartilhada | Estado mutável, valores e pedido de cancelamento | entre Steps |
| Workflow Result | Relatório final | Snapshot com status, tempos, Steps e falha | retorno do Orchestrator |
| Workflow Status | Situação do roteiro | created/running/completed/failed/cancelled | lifecycle genérico |
| Workflow Engine | Intérprete do roteiro | Fachada que valida e executa uma Definition | `asep.workflow.engine` |
| Workflow Validator | Revisor do roteiro | Validação estrutural e de policy | antes do Executor |
| Workflow Executor | Condutor das tarefas | Loop sequencial, Context, status e Timeline | Engine |
| Execution Policy | Regras do percurso | stop-on-failure e cancelamento | WorkflowDefinition |
| Agent | Especialista sob contrato | Protocol com metadata e execute(request, context) | `asep.agents` |
| Agent Capability | Habilidade declarada | Identificador e descrição de capacidade | AgentMetadata |
| Agent Request | Ordem de trabalho | Objetivo, inputs e metadados imutáveis | entrada do Agent |
| Agent Step Adapter | Intérprete entre especialista e roteiro | Implementa WorkflowStep e delega ao Agent | integração com Engine |
| Agent Registry | Lista telefônica de especialistas | Porta para registrar e consultar Agents | composição da aplicação |
| Registration | Inclusão na lista | Associação única de AgentId a Agent | `register` |
| Agent Resolution | Localização de especialista | Recuperação determinística por AgentId | `get` |
| Capability Lookup | Busca por habilidade | Filtro case-sensitive pelo ID da capacidade | `find_by_capability` |
| Duplicate Registration | Dois cadastros com mesmo código | Violação de unicidade que preserva o original | exceção específica |
| Composition Root | Local de montagem | Ponto que cria Registry e conecta dependências | startup futuro |
| In-Memory Registry | Lista temporária | Dicionário encapsulado por instância | Sprint 8.4 |
| Agent Lifecycle | Vida da lista de agentes | criar, registrar, usar e descartar | controlado pela composição |
| Workflow Snapshot | Fotografia do roteiro executado | DTO imutável e JSON-safe do resultado | persistência da Sprint 8.5 |
| Workflow Repository | Arquivo de fotografias | Porta de CRUD e queries de snapshots | memory/file/sqlite |
| Workflow Persistence Service | Fotógrafo do workflow | Transforma Definition + Result em Snapshot | integração no Orchestrator |
| Snapshot History | Álbum de execuções | vários snapshot IDs por Workflow ou Run | preservação histórica |
| Architecture Hardening | Revisão antes da entrega | redução comprovada de inconsistências sem nova função | Sprint 8.6 |
| Release Candidate | Versão candidata | build validado que ainda depende de gates de publicação | RC1 |
| Audit Evidence | Prova da revisão | comando, métrica ou inspeção reproduzível | `docs/audits` |

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
