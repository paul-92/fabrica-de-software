# ASEP Self-development

**Versão:** 0.1.3  
**Status:** Architecture concluída; aguardando aprovações  
**Última atualização:** 2026-07-28

## Objetivo
Usar a ASEP para especificar e, após aprovação futura, desenvolver a própria ASEP.
## Escopo
Nesta etapa, somente estrutura, perguntas, riscos e artefatos documentais; sem Runtime ou integração de IA.
## Workflow
`software-project`, versão 0.1.0.
## Agentes
Orchestrator, Business Analyst, Software Architect, Project Manager, QA, Security, DevOps e Documentation; especialistas adicionais serão condicionais.
## Entregáveis
Brief, análise validada, arquitetura/ADRs, plano, evidência, relatórios e retrospectiva.

### Entregáveis atuais

- [Business Analysis](business-analysis/executive-summary.md);
- [catálogo de requisitos](business-analysis/requirements.md);
- [proposta de MVP](business-analysis/mvp.md);
- [perguntas abertas](business-analysis/open-questions.md);
- [log da execução](logs/execution-log.md);
- [review e quality gate](reports/business-analysis-review.md).
- [Architecture Overview](architecture/architecture-overview.md);
- [catálogo de ADRs](architecture/architecture-decisions.md);
- [Architecture Review](reports/architecture-review.md).
## Critérios de sucesso
Contexto rastreável, decisões humanas nomeadas, workflow executável sem referências quebradas e piloto futuro mensurável.
## Perguntas pendentes
Quem assume papéis humanos? Qual ambiente e orçamento? Qual nível de autonomia? Quais dados e integrações podem ser usados?
## Próximos passos
Paulo Cesar revisa/aprova a Arquitetura; Security Engineer revisa a baseline de
segurança; Product Owner e Architect resolvem a ordem sequencial do workflow 0.1.
Não avançar para Planning nem implementar código até a reaplicação do `QG-ARCH`.
