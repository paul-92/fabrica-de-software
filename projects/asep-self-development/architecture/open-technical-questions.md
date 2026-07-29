# Open Technical Questions

**ID:** ARCH-OQ-001 | **Versão:** 0.1.0 | **Status:** open

| ID | Pergunta | Dono | Impacto/gatilho |
|---|---|---|---|
| TQ-001 | Qual ordem sequencial substitui `planning_design` e `assurance` paralelos no workflow 0.1? | Product Owner + Architect | bloqueia plano T0 |
| TQ-002 | Quais sistemas operacionais locais são suportados? | Product/Operations | testes de lock/replace |
| TQ-003 | Qual retenção mínima de logs/audit/artifacts? | Product/Security | política operacional |
| TQ-004 | Quais targets de volume e tempo do piloto? | Product/Operations | NFR-008 |
| TQ-005 | A aprovação local por papel declarado é suficiente para o piloto? | Product/Security | risco TR-004 |
| TQ-006 | Qual estrutura de empacotamento/distribuição será usada? | Architect/DevOps | planejamento |
| TQ-007 | O BA Adapter gera novos drafts ou valida/renderiza dados fornecidos? | Product/BA | detalhamento T4 |
| TQ-008 | Quem exercerá Security e Quality nos reviews posteriores? | Executive | gates futuros |

## Decisão humana imediata

Paulo Cesar deve aprovar ou solicitar alterações nos ADRs e responder TQ-001 antes
de liberar Planning. As demais perguntas podem entrar no plano com donos e marcos,
desde que não sejam silenciosamente assumidas.
