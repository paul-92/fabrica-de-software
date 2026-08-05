# Fase 20 — Intelligent Integration

**Público:** engenharia, arquitetura e consumidores da futura camada de aplicação  
**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** concluída

## Objetivo

Disponibilizar conhecimento aprendido ao Planning pela fronteira de memória
existente e compor Planning com Autonomous Engineering sem fundir os domínios
ou transferir responsabilidades entre eles.

## Fluxo implementado

```text
Memory
  ↓
Knowledge Retrieval
  ↓
KnowledgeAwareContext
  ↓
KnowledgeAwarePlanningAdapter
  ↓
Planning
  ↓
IntelligentEngineeringService
  ├─ PlanningResult
  └─ AutonomousEngineeringResult
          ↓
      LearningService
          ↓
        Memory
```

O fluxo torna conhecimento recuperado disponível a um consumidor posterior.
Ele não executa as recomendações armazenadas nem transforma reflexão em
controle de fluxo.

## 20.1 — Knowledge-Aware Context

`KnowledgeAwareContext` preserva contexto base, `MemoryEntry` recuperadas,
quantidade de conhecimento e metadados. `KnowledgeContextBuilder` define a
porta de composição e `DeterministicKnowledgeContextBuilder` apenas combina
as entradas recebidas. O builder não faz retrieval, parsing textual ou
persistência.

## 20.2 — Knowledge-Aware Planning

`KnowledgePlanningAdapter` e `KnowledgeAwarePlanningAdapter` convertem a
entrada enriquecida em um novo `PlanningRequest`. O conhecimento aprendido
reutiliza `PlanningContext.memory`, sem criar campo paralelo. A memória
existente vem primeiro; novas entradas mantêm sua ordem e são deduplicadas por
`memory_id`.

`PlanningEngine`, `PlanningContext`, `SequentialPlanningStrategy` e
`PlanningValidator` não foram modificados para conhecer Learning ou
Intelligence.

## 20.3 — Intelligent Engineering Integration

`AutonomousEngineeringExecutor` é a porta mínima do pipeline autônomo.
`IntelligentEngineeringRequest` recebe explicitamente `PlanningRequest`,
`KnowledgeAwareContext` e `AutonomousEngineeringRequest`.
`IntelligentEngineeringService` adapta e executa Planning uma vez, executa
Autonomous Engineering uma vez e devolve `IntelligentEngineeringResult` com a
requisição adaptada e os dois resultados originais.

`PlanningResult` continua representando o planejamento da plataforma;
`AutonomousEngineeringResult` continua reunindo proposta, `RepairPlan`,
`RepairResult` e `EngineeringReflection`. Não existe conversão artificial
entre esses modelos.

## 20.4 — End-to-End Intelligent Integration

O teste integrado comprova uma execução anterior persistindo conhecimento por
`LearningService`, sua recuperação, composição em contexto, consumo pelo
Planning, execução separada de Autonomous Engineering e persistência do novo
aprendizado. Uma consulta posterior recupera ambas as experiências.

O cenário também cobre isolamento por agente, exclusão de memórias comuns,
preservação das entradas originais, deduplicação e ausência de nova execução
quando `should_retry=True`. Nenhum código adicional de produção foi
necessário na Sprint 20.4.

## Fronteiras

- Intelligence depende de contratos e não acessa storage diretamente;
- Planning não conhece Learning nem `KnowledgeRetriever`;
- `AutonomousEngineeringService` não conhece Memory;
- `recommended_actions` informa decisões, mas nunca é executado pela camada;
- `should_retry` permanece recomendação, não comando;
- não há retrieval ou persistência implícitos no serviço de integração;
- não há IA externa nem retry automático introduzido pela Fase 20;
- efeitos de reparo permanecem atrás dos contratos existentes da Fase 17.

## Evidência

`tests/qa/intelligence` cobre modelos imutáveis, contratos, API pública,
adaptação e deduplicação de memória, integração com `PlanningEngine`,
composição dos subsistemas e o fluxo E2E de aprendizado e recuperação.

## Próxima fase

A [Fase 21 — Application/API Layer](../phase-21/application-api-layer.md)
concluiu a fachada estável e o adapter HTTP para interfaces externas.

## Decisões

Nenhum ADR novo foi necessário. A fase aplica as fronteiras já estabelecidas
de Memory, Planning, Learning, Repair e composição por contratos.
