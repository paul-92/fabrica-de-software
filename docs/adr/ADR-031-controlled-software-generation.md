# ADR-031 — Geração de software mediada por Tools

**Status:** aceito pela implementação da Fase 16 | **Versão:** 1.0

## Contexto

Materializar e testar software exige efeitos no filesystem e subprocessos sem
conceder acesso irrestrito aos agentes.

## Decisão

Agents nunca escrevem diretamente no filesystem. Escrita e validação ocorrem
por `WriteFileTool` e `RunTestsTool`, via `ToolExecutionService`. O workspace é
a fronteira de segurança, a resolução de paths é centralizada e overwrite é
explícito. `PlanStep.metadata` transporta opções específicas; resultados
anteriores usam `AgentExecutionRequest.inputs["previous_results"]`. Quality
Gate permanece fora do `DeveloperAgent` e falhas técnicas percorrem os
contratos existentes.

## Consequências

Efeitos ficam testáveis e auditáveis e não se criam contratos paralelos. A
geração atual é determinística, limitada às capacidades registradas e não
constitui autonomia de IA. Evidência: `src/asep/tools/builtin.py`,
`src/asep/tools/workspace.py`, `src/asep/agents/developer.py`, Coordinator e
testes E2E das Fases 14–16.

