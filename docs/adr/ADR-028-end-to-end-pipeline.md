# ADR-028 — Fachada pública e pipeline ponta a ponta

**Status:** aceito  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

Os componentes da Fase 9 funcionavam isoladamente, mas o consumidor precisava
conhecer detalhes de composição para executar um objetivo.

## Decisão

Criar `ASEPEngine` como fachada pública, `ExecutionPipeline` como coordenador do
caso de uso e `PipelineBuilder` como composition root. A fachada recebe um
objetivo e retorna `GoalResult`; não expõe componentes internos.

O Pipeline reutiliza Workflow, Planning, Coordination, Supervisor, Runtime,
Tools, Memory, Timeline e métricas por suas APIs existentes. O Builder conecta
implementações, mas não executa lógica de negócio.

## Desacoplamento

Cada mecanismo continua substituível por contrato. `ASEPEngine` depende apenas
de `ExecutionPipeline`; futuras entradas CLI, REST ou Web poderão chamar a
fachada sem conhecer a composição. Uma futura integração com LLM deverá entrar
atrás de um contrato existente, sem alterar `GoalRequest` ou `GoalResult`.

## Alternativas consideradas

- função monolítica: rejeitada por misturar composição e execução;
- expor todos os serviços ao usuário: rejeitada por acoplamento;
- ampliar WorkflowEngine: rejeitada por transformá-lo em composition root;
- criar CLI ou REST agora: rejeitada por escopo.

## Consequências

A API `asep.execute` fica simples e testável. A composição padrão usa storage
em memória e um agente determinístico. Persistência de artefatos e configuração
externa do pipeline permanecem evoluções futuras.

## Evidência

`src/asep/pipeline/`, `src/asep/agents/developer.py`,
`tests/test_execution_pipeline.py` e `examples/`.
