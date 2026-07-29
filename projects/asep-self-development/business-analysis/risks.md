# Registro de Riscos

**ID:** BA-RSK-001 | **Versão:** 0.1.1 | **Status:** aberto  
**Dono:** Business Analyst | **Data:** 2026-07-28

| ID | Risco | Prob. | Impacto | Resposta proposta | Dono |
|---|---|---|---|---|---|
| R-001 | se mudanças futuras forem tratadas como aprovadas sem change control, a arquitetura pode divergir da baseline | média | alto | preservar aprovações e exigir change request | Orchestrator/Product |
| R-002 | se o MVP tentar executar agentes de IA, complexidade ocultará a validação do lifecycle | média | alto | manter execução de etapas/controlos, sem IA obrigatória | Product |
| R-003 | se interfaces declarativas mudarem sem schema, executor e documentos divergirão | alta | alto | schemas/testes na 0.2 | Tech Lead |
| R-004 | se estado não for íntegro, retomada e auditoria serão não confiáveis | média | alto | critérios de atomicidade e cenários de falha | Architecture/QA |
| R-005 | se logs capturarem contexto integral, segredos ou dados podem vazar | média | alto | minimização, redaction e testes | Security |
| R-006 | se CLI não for validada com operador, comandos podem ser ambíguos | média | médio | teste de tarefas | Product/UX |
| R-007 | se documentos históricos forem aceitos como canônicos, versões podem divergir | média | médio | usar apenas Registry e avisos de compatibilidade | Orchestrator |
| R-008 | se metas de desempenho forem inventadas, decisões técnicas serão injustificadas | média | médio | definir após cenário/ambiente | Product/Operations |
| R-009 | se cancelamento/retomada não cobrirem efeitos parciais, execução poderá corromper estado | média | alto | cenários de aceitação e design específico | Architecture/QA |

Nenhum risco material foi aceito nesta análise.
