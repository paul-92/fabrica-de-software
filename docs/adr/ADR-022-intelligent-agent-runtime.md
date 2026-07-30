# ADR-022 — Runtime separado para agentes inteligentes

**Status:** aceita localmente  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

A Fase 8 definiu `Agent`, `AgentRegistry`, Workflow Engine e
`AgentStepAdapter`. Executar um agente passa a exigir resolução, validação,
política, correlação, observabilidade, tradução de erros e idempotência. Colocar
essas tarefas no Engine, no Registry ou no próprio agente violaria suas
responsabilidades atuais.

## Decisão

Criar a porta síncrona `asep.agents.AgentRuntime` e implementá-la com
`AgentExecutionService`.

- o Registry apenas registra e resolve agentes;
- o Workflow Engine executa Steps e não conhece agentes ou Registry;
- o `AgentStepAdapter` converte o runtime em uma Step;
- retry, timeout, Timeline, métricas e erros pertencem ao runtime;
- dependências são injetadas por contratos;
- o runtime não conhece providers ou repositories concretos.

A API permanece síncrona porque o Engine e o contrato `Agent.execute` são
síncronos. Retry é limitado, explícito e sem backoff. Timeout mede a duração e
classifica o retorno; não tenta matar uma chamada Python. Idempotência e
exclusão de duplicidade são locais à instância.

## Por que não usar componentes existentes diretamente

O `asep.runtime.AgentRuntime` histórico recebe modelos do Registry de projetos
e sustenta o Orchestrator sequencial. Reescrevê-lo nesta Sprint aumentaria
escopo e risco. O contrato novo usa os agentes formais da Fase 8 e coexiste com
o caminho legado até uma migração intencional.

O resultado do runtime também não substitui o resultado de provider: providers
adaptam processos externos; o runtime descreve o lifecycle de um Agent.

## Alternativas consideradas

1. **Engine chama Agent diretamente:** rejeitada por acoplar retry, Registry e
   observabilidade ao loop.
2. **Registry executa Agent:** rejeitada porque Registry é catálogo, não
   serviço de aplicação.
3. **API assíncrona agora:** rejeitada por incompatibilidade com contratos
   existentes e ausência de necessidade comprovada.
4. **Timeout por thread/processo:** rejeitada nesta fase por não garantir
   cancelamento seguro e por ampliar a infraestrutura.
5. **Lock/persistência distribuídos:** rejeitados; não há execução distribuída
   autorizada nesta Sprint.

## Consequências

Positivas:

- Engine, Registry e providers permanecem isolados;
- políticas e observabilidade são testáveis com fakes;
- falhas possuem dados estruturados e exceções tipadas;
- novos agentes podem reutilizar o mesmo lifecycle.

Custos:

- coexistem dois contratos chamados `AgentRuntime` em namespaces distintos;
- timeout não é preemptivo;
- cache, duplicidade e métricas online não são duráveis.

## Segurança

Eventos não carregam input/output. Metadados derivados removem chaves sensíveis
recursivamente, e exceções inesperadas são reduzidas ao tipo. O runtime não lê
variáveis de ambiente.

## Evidências

Implementação em `src/asep/agents/` e testes em
`tests/test_agent_runtime.py`. Documentação operacional:
[Agent Runtime](../agents/AgentRuntime.md).

