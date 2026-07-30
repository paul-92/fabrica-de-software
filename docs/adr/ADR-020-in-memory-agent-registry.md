# ADR-020 — Agent Registry em memória e sem estado global

**Status:** aceito localmente  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto e problema

Agentes precisam ser localizados por identidade e capacidade sem acoplar o
Workflow Engine a implementações, providers ou infraestrutura.

## Alternativas

- dicionário global ou Singleton;
- Registry persistente/configurável;
- lookup simples injetado e em memória;
- descoberta dinâmica de classes.

## Decisão

Definir uma porta `AgentRegistry` e implementar
`InMemoryAgentRegistry`, criado pela composição. Usar `AgentId` como chave
única, rejeitar duplicidade, ordenar listagens por ID e consultar capacidades
por identificador exato. O Engine não conhece o Registry.

## Justificativa

O uso atual é pequeno, síncrono e local. Um dicionário encapsulado oferece
clareza, previsibilidade e testes isolados sem antecipar persistência ou
concorrência.

## Consequências e benefícios

- ausência de estado global entre testes;
- lookup determinístico;
- substituição futura pela porta;
- agente original preservado em duplicidade;
- composição explícita com `AgentStepAdapter`.

## Limitações e evolução

O conteúdo desaparece com a instância e não há thread safety explícita,
versionamento composto, plugins ou ranking. Persistência e Workflow Persistence
permanecem fora da Sprint 8.4 e exigirão decisão própria.

