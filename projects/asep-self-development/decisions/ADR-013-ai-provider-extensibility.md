# ADR-013 — Extensibilidade futura para provedores de IA

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
IA externa está fora do MVP, mas agentes futuros podem precisar dela.
## Problema
Evitar acoplamento futuro sem implementar abstração especulativa.
## Alternativas
Ignorar; integrar provedor agora; definir somente `AgentPort`.
## Decisão
Runtime depende de `AgentPort`; 0.1 implementa apenas Business Analyst Adapter
determinístico. Não criar `AIProvider`, SDK, configuração ou rede agora.
## Justificativa
O ponto de extensão é o agente, suficiente para substituir o adaptador quando
requisitos/política existirem.
## Consequências
Integração futura exige ADR, política de dados, threat model e novo adaptador.
## Riscos
Porta ser insuficiente a streaming/tool use. Evoluir por casos reais e versionar
contrato, não antecipar capacidades.
