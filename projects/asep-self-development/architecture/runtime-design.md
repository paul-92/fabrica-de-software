# Agent Runtime Design

**ID:** ARCH-RUN-001 | **Versão:** 0.1.0 | **Status:** approved

## Responsabilidade

Executar o lifecycle de um agente por contrato, dentro do processo local, e
devolver resultado estruturado. Não seleciona workflow nem decide gate.

## Lifecycle

Load → Validate → Load Contract → Load Knowledge → Load Standards → Load Context
→ Execute → Self Review → Output Validation → Generate Artifacts → Handoff → Finish.

Na versão 0.1, `Execute` chama um `AgentPort` determinístico. O único adaptador
executável é Business Analyst Adapter. Ele recebe conteúdo declarado e templates;
não gera fatos, pesquisa, requisitos ou decisões por inferência.

## Interface

```text
AgentPort.execute(AgentTask, AgentContext) -> AgentResult
Runtime.run(contract, task, context) -> RuntimeOutcome
```

`AgentResult` contém status, outputs propostos, findings, events e handoff. O
Runtime valida required outputs antes de permitir registro.

## Isolamento

- contexto mínimo e paths allowlisted;
- sem rede e sem subprocessos no adaptador 0.1;
- clock/ID/filesystem injetados;
- timeout cooperativo não é requisito até existir efeito externo;
- uma execução por vez sob lock do projeto.

## Falhas e testes

Falha de contrato, entrada, template, output ou artifact é tipada e não conclui
etapa. Testes de contrato usam adaptadores fake, golden Markdown e cenários de
output ausente, exceção e cancelamento.
