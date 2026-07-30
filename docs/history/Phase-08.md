# Fase 08 — Coordenação de workflows

**Dono:** Engenharia ASEP | **Versão:** 1.1 | **Status:** concluída localmente

## Visão Geral

A Fase 08 começa com infraestrutura genérica de coordenação.

## O Problema

Integrar agentes antes de provar lifecycle, falha e observabilidade aumentaria
risco e acoplamento.

## A Solução

Sprint 8.1 implementa Steps simuláveis e execução sequencial observável.
Sprint 8.2 separa interpretação e execução em `WorkflowEngine`.
Sprint 8.3 define contratos formais de agentes e interoperabilidade por adapter.
Sprint 8.4 adiciona um Registry em memória, isolado e determinístico.
Sprint 8.5 persiste snapshots completos de workflow nos três backends.
Sprint 8.6 audita e endurece a arquitetura para o RC1, sem funcionalidade nova.

## Explicação simples

Primeiro construímos o maestro e ensaiamos com músicos simulados; agora existe
uma ficha formal para integrar futuros músicos.

## Explicação técnica

O Orchestrator projeta estados em Run e Timeline; Metrics/Dashboard leem.

## Componentes

Modelos de workflow, Orchestrator, Engine, contratos e Registry de agentes,
WorkflowSnapshot e infraestrutura da Fase 07.

## Fluxo completo

`Workflow -> Steps -> terminal result -> query/metrics/dashboard`.

## Dependências

A Fase 08 reutiliza persistência configurável da Fase 07.

## Exemplos

Uma Step pode alterar Context, falhar por exceção ou solicitar cancelamento.

## Testes

12 testes da Sprint e regressão de 612 casos.

## Limitações

Estado atual é sequencial, síncrono e sem novos agentes inteligentes concretos.

## Evolução futura

Será registrada apenas quando implementada.

## Referências

[Sprint 8.1](../phase-08/Sprint-8.1-Workflow-Orchestrator.md).
[Sprint 8.2](../phase-08/Sprint-8.2-Workflow-Engine.md).
[Sprint 8.3](../phase-08/Sprint-8.3-Agent-Contracts.md).
[Sprint 8.4](../phase-08/Sprint-8.4-Agent-Registry.md).
[Sprint 8.5](../phase-08/Sprint-8.5-Workflow-Persistence.md).
[Sprint 8.6](../phase-08/Sprint-8.6-Architecture-Hardening-RC1.md).

## Relacionado a

Fase 08; ADRs 017–021; Workflow; Agents; Persistence; testes; Roadmap.
