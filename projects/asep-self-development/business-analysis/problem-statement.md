# Problem Statement

**ID:** BA-PS-001 | **Versão:** 0.1.0 | **Status:** proposta  
**Dono:** Business Analyst | **Data:** 2026-07-28

## Problema

A ASEP possui uma especificação documental capaz de descrever projetos, agentes,
contratos, workflows e gates, mas ainda não existe uma forma executável de aplicar
essas definições de maneira consistente. Hoje, uma pessoa precisa interpretar os
documentos, manter o estado e registrar evidências manualmente, o que permite
divergência entre intenção, execução e auditoria.

## Pessoas e operação afetadas

- Orchestrator, que não possui mecanismo executável para instanciar e controlar o fluxo;
- especialistas, que dependem de entradas e handoffs consistentes;
- responsáveis humanos, que precisam visualizar e decidir aprovações;
- Quality e Governance, que precisam verificar estado, gates e evidências.

Paulo Cesar foi confirmado como Product Owner; os demais responsáveis ainda
precisam ser nomeados conforme os gates posteriores.

## Resultado desejado

Permitir que uma pessoa use uma interface local de linha de comando para iniciar
e acompanhar um projeto ASEP, executando etapas sequenciais e controles essenciais
com estado e rastreabilidade. O resultado não pressupõe execução autônoma por IA.

## Evidências disponíveis

- [core/SYSTEM.md](../../../core/SYSTEM.md) define o fluxo operacional esperado;
- [workflows/software-project.yaml](../../../workflows/software-project.yaml)
  descreve o lifecycle declarativo;
- [reports/open-decisions.md](../../../reports/open-decisions.md) demonstra que
  autoridades, política de dados e primeiro incremento ainda aguardam decisão.

## Hipótese principal

Um executor local e sequencial é suficiente para validar as interfaces da ASEP
antes de investir em paralelismo, serviço remoto ou integração com IA.

**Impacto se falsa:** o MVP poderá não provar a utilidade operacional.  
**Dono da validação:** Product Owner — Paulo Cesar.  
**Gatilho:** execução do primeiro cenário piloto aprovado.
