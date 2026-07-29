# Quality Gates

**Dono:** Quality Lead; **status:** ativo

Gates usam critérios observáveis, não percentuais subjetivos. Cada gate registra ID, critérios, evidências, avaliador, decisão, data, achados e exceções.

| Gate | Critérios verificáveis | Evidência obrigatória |
|---|---|---|
| QG-INTAKE | sponsor, objetivo, tipo, dados e restrições identificados | brief e classificação |
| QG-DISCOVERY | problema, fontes, hipóteses e decisão documentados | síntese validada |
| QG-ANALYSIS | requisitos, regras, escopo e aceite rastreáveis | catálogo e aprovação |
| QG-ARCH | atributos, alternativas, fronteiras e falhas tratados | arquitetura + ADRs |
| QG-PLAN | entregas, dependências, riscos e responsáveis definidos | backlog e roadmap |
| QG-DESIGN | jornadas, estados, conteúdo e acessibilidade revisados | protótipo/especificação |
| QG-IMPLEMENT | critérios vinculados, checks e revisão concluídos | mudança e relatórios |
| QG-TEST | riscos e jornadas críticas cobertos, defeitos classificados | plano e relatório |
| QG-SECURITY | threat model, controles e achados tratados | revisão de segurança |
| QG-DEPLOY | rollback, observação, runbook e go/no-go prontos | plano e aprovação |
| QG-DOC | público, operação e mudanças documentados | documentação revisada |
| QG-HANDOVER | ativos, acessos, pendências e ownership transferidos | aceite do receptor |
| QG-CLOSE | aceite, retenção, métricas e retrospectiva concluídos | relatório de encerramento |

Falha bloqueia a transição ou gera exceção formal com dono, validade e plano. Catálogo: `registry/quality-gates.yaml`.
