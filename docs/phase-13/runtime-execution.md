# Fase 13 — Coordenação até o Agent Runtime

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída

## Objetivo e evidência

Fechar a integração entre `PlanningResult`, `AgentCoordinatorAdapter` e o
runtime real de agentes. O adapter cria o contexto de coordenação; o
Coordinator resolve capacidades e delega a execução ao contrato do Runtime.

O commit `6231e44` e `tests/qa/agents/coordination/test_end_to_end.py`
comprovam o caminho ponta a ponta. `9ca3525` acrescenta a propagação de metadata
do planejamento para o contexto de execução. Planning não executa agentes ou
Tools; Coordination não executa Tools diretamente.

## Contrato preservado

Cada `PlanStep` gera uma solicitação de execução com dados da etapa e opções do
contexto. O resultado retorna pela coordenação e é agregado em
`CoordinationResult`. O isolamento entre Planning, Registry, Coordinator e
Runtime permanece o definido pelos ADRs 025, 026 e 028.

