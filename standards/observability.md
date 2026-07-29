# Standard: observability

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- Logs, métricas e traces usam IDs de correlação, classificação e retenção; alertas são acionáveis.
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- Instrumentar jornadas e dependências críticas, ligando alerta a dashboard e runbook.

## Opção dependente do contexto

- Sinais e granularidade dependem de SLO, risco, custo e necessidades de diagnóstico.

## Evidência obrigatória

- Evidência: catálogo de eventos, consultas/dashboards, teste de alerta e ausência de dados indevidos.

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
