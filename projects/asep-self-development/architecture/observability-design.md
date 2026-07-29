# Observability Design

**ID:** ARCH-OBS-001 | **Versão:** 0.1.0 | **Status:** approved

## Objetivo

Explicar estado e falha de uma execução local sem dashboard ou backend de
telemetria. Observability 0.1 é composta por eventos estruturados, status CLI e
relatório derivável.

## Sinais

- eventos do catálogo: project/workflow/stage/agent/gate/approval/artifact;
- duração local por comando/etapa, sem target inventado;
- contadores deriváveis: tentativas, bloqueios, falhas e gates;
- status atual de projeto/workflow/etapas;
- correlação por trace, workflow_run, stage_run e attempt.

## Instrumentação

Casos de uso emitem eventos de domínio; adaptador de logging decide apresentação.
Componentes não escrevem mensagens livres diretamente. Clock é injetado. Payloads
usam schema e classificação.

## Diagnóstico

`asep status --json` mostra snapshot; `asep status` mostra tabela Rich; um comando
futuro `audit verify` é Should/backlog, não MVP Must. Sem metrics server, tracing
distribuído, alerta, dashboard ou envio externo.

## Critérios

Para um cenário de aceitação, deve ser possível reconstruir: comando → etapa →
agente → artefato → gate → aprovação → próximo estado. Falhas exibem código,
correlation ID e próxima ação.
