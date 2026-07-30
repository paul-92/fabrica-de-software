# Sprint 9.1 — Intelligent Agent Runtime

**Público:** engenharia, arquitetura e QA  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementada localmente

## Objetivo

Iniciar a Fase 9 com uma infraestrutura determinística para executar os agentes
formais criados na Fase 8, sem introduzir agentes autônomos ou novos providers.

## Escopo entregue

- porta `AgentRuntime` e serviço `AgentExecutionService`;
- request, contexto, resultado, status e política imutáveis;
- validator e hierarquia de exceções;
- resolução exclusiva pelo `AgentRegistry`;
- eventos específicos de agente na Timeline;
- porta e coletor local de métricas;
- retry explícito, timeout observacional e cancelamento antes do início;
- idempotência local por `execution_id`;
- modo runtime no `AgentStepAdapter`;
- compatibilidade formal e histórica do `BusinessAnalystAgent`;
- filtragem de metadata sensível e representações seguras.

## Arquitetura e fronteiras

O Workflow Engine conhece apenas sua Step. O adapter conhece a porta do
runtime. O serviço conhece contratos de Agent, Registry, Timeline e métricas,
mas não conhece Workflow Engine, repositórios concretos, ambiente, SQLite ou
providers.

O `asep.runtime.AgentRuntime` histórico permanece responsável pelo caminho
sequencial legado. O novo contrato está em `asep.agents.AgentRuntime`; a
separação preserva compatibilidade e evita uma reescrita do fluxo existente.

## Decisões

- API síncrona para seguir o Engine atual;
- Registry localiza, mas não executa;
- política padrão segura: uma tentativa e fail-fast;
- resultados terminais estruturados, com exceções tipadas para falhas
  fail-fast;
- Timeline sem conteúdo integral de input/output;
- métricas por porta injetável, sem nova dependência;
- controle de duplicidade apenas por instância nesta fase.

Essas decisões estão registradas no
[ADR-022](../adr/ADR-022-intelligent-agent-runtime.md).

## Validações e evidências

Os testes novos exercitam o lifecycle e as fronteiras com fakes determinísticos,
sem rede, sleep longo ou provider real. A suíte completa, cobertura,
`compileall` e verificações de Git compõem o gate final.

## Fatos e hipóteses

Fato: o Engine e os agentes formais atuais são síncronos.  
Fato: `MetricsService` é uma projeção de Runs e não um gravador online.  
Decisão: criar uma porta mínima de gravação e um coletor em memória no domínio
de agentes, sem alterar esse serviço existente.  
Hipótese futura: cancelamento cooperativo ou persistência de métricas poderá
exigir novas portas; nenhuma foi antecipada aqui.

## Riscos e limitações

- uma execução bloqueada em código do agente não é interrompida pelo timeout;
- idempotência não sobrevive ao reinício e não coordena múltiplos processos;
- métricas online não são duráveis;
- as mudanças da Fase 8 e desta Sprint continuam pendentes de revisão e commit.

## Checklist

- [x] runtime e modelos definidos;
- [x] validação anterior à execução;
- [x] Registry, Timeline, métricas e Workflow integrados;
- [x] segurança e idempotência local testadas;
- [x] compatibilidade preservada;
- [x] documentação e ADR produzidas;
- [ ] publicação/commit autorizados por pessoa responsável.

## Próxima ação

Responsável: mantenedor autorizado. Gatilho: após gate técnico verde, revisar o
diff acumulado e decidir commit/publicação. A Sprint 9.2 não foi iniciada.

## Referências

[Agent Runtime](../agents/AgentRuntime.md),
[Architecture Map](../architecture/ArchitectureMap.md) e
[Current Sprint Prompt](../../prompts/CurrentSprintPrompt.md).

