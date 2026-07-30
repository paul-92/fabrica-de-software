# Agent Runtime

**Público:** engenharia e mantenedores da ASEP  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

## Visão Geral

O runtime inteligente é a fronteira síncrona que executa um `Agent` formal.
Ele resolve o agente pelo `AgentRegistry`, valida a requisição, aplica a
política, registra Timeline e métricas e devolve um resultado imutável.

## O Problema

Chamar agentes diretamente no Workflow Engine misturaria coordenação,
resolução, retry, observabilidade e regras de segurança. O Registry, por sua
vez, deve apenas registrar e localizar agentes.

## A Solução

```text
WorkflowEngine -> AgentStepAdapter -> AgentRuntime
                                      |
                                      v
                             AgentExecutionService
                              /       |        \
                    AgentRegistry  Timeline  Metrics port
                          |
                          v
                        Agent
```

`AgentRuntime` é um `Protocol`; `AgentExecutionService` é a implementação
concreta. Todas as dependências são injetadas.

## Explicação simples

O runtime funciona como uma sala de controle: confere quem executará, valida a
ordem de serviço, acompanha a execução e produz um comprovante estruturado.

## Explicação técnica

### Contratos públicos

- `AgentExecutionRequest`: identidade, agente, capability, payload, contexto,
  correlação, timeout e metadados;
- `AgentExecutionContext`: tentativa, deadline e correlação imutáveis;
- `AgentExecutionResult`: status terminal, duração, erro e resultado formal;
- `AgentExecutionPolicy`: timeout, tentativas, retry, capability e fail-fast;
- `AgentExecutionValidator`: valida registry e capability antes de executar;
- `AgentRuntime`: porta síncrona;
- `AgentExecutionService`: coordenação concreta.

Os modelos são Pydantic estritos, imutáveis e aceitam somente dados JSON nos
payloads públicos. O resultado deste módulo não é o
`asep.providers.AgentExecutionResult`: o primeiro descreve o ciclo do agente;
o segundo é um contrato interno da fronteira de providers.

### Ciclo de vida

```text
requested -> validated -> started
                           |  \
                           |   -> retrying -> started
                           v
             succeeded | failed | rejected | timed_out

requested -> cancelled
```

Eventos carregam identificadores, capability, tentativa, correlação, status e
tipo do erro. Input e output não são copiados para a Timeline.

### Erros e fail-fast

Falhas esperadas podem ser devolvidas como `failed`, `rejected`, `cancelled`
ou `timed_out`. Com `fail_fast=True`, rejeições de validação e exceções de
execução usam a hierarquia `AgentRuntimeError`. Mensagens externas são
sanitizadas e preservam apenas a classificação necessária.

### Retry e timeout

O padrão é uma tentativa, sem retry. Retry exige habilitação explícita e só
ocorre para erro marcado como recuperável; erros inesperados só são repetidos
se `retry_unexpected_errors=True`.

O timeout desta versão é determinístico e observacional: mede a duração
síncrona e classifica o resultado após o retorno do agente. Ele não interrompe
uma função Python bloqueada. A evolução para interrupção cooperativa exige
novo contrato de cancelamento.

### Idempotência

Uma instância mantém resultados por `execution_id`. Nova chamada concluída
devolve o mesmo objeto sem reexecutar; chamada simultânea igual é rejeitada.
O controle é local ao processo e não constitui lock distribuído ou durável.

### Segurança

`input`, `output`, contexto e metadata têm representação textual reduzida.
Chaves `password`, `secret`, `token`, `api_key` e `authorization` são removidas
recursivamente dos metadados derivados. Variáveis de ambiente não são lidas.
Agentes ainda recebem o payload original, pois ele é a entrada de domínio.

### Métricas

`AgentExecutionMetricsRecorder` recebe cada resultado terminal. A implementação
em memória agrega totais, status, retries, duração, agente e capability. Ela
não adiciona biblioteca externa e não altera o `MetricsService`, que continua
projetando métricas históricas a partir de Runs.

## Integração com agentes existentes

`BusinessAnalystAgent` agora publica `AgentMetadata` e aceita tanto a chamada
formal `(AgentRequest, AgentContext)` quanto sua chamada histórica
`execute(AgentContext)`. O runtime não conhece regras desse agente.

## Testes

`tests/test_agent_runtime.py` cobre sucesso, validação, falha, retry, timeout,
cancelamento, Timeline, métricas, privacidade, idempotência, Registry,
Business Analyst e Workflow Engine.

## Limitações

- execução exclusivamente síncrona e sequencial;
- timeout sem preempção;
- cache e proteção contra duplicidade somente em memória;
- sem backoff, scheduler, fila, circuit breaker ou execução distribuída;
- métricas do runtime não são persistidas nesta Sprint.

## Evolução futura

Persistência ou cancelamento cooperativo devem depender de novas portas, sem
acoplar o runtime a SQLite ou providers. Planejamento multiagente, RAG e agentes
autônomos permanecem fora desta Sprint.

## Referências

[Sprint 9.1](../phase-09/Sprint-9.1-Intelligent-Agent-Runtime.md),
[ADR-022](../adr/ADR-022-intelligent-agent-runtime.md) e
[Agent Contracts](../workflows/AgentContracts.md).

