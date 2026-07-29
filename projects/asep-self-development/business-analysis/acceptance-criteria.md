# Critérios de Aceite

**ID:** BA-AC-001 | **Versão:** 0.1.0 | **Status:** proposta  
**Dono:** Business Analyst | **Data:** 2026-07-28

## Funcionais

| ID | Critério |
|---|---|
| AC-001 | Dado registro válido, quando criar/abrir, então o projeto recebe identidade e estado consultável; registro inválido não cria execução. |
| AC-002 | Dado Registry válido, quando carregar, então catálogos e versões ficam disponíveis; YAML inválido produz erro acionável. |
| AC-003 | Dada referência inexistente/incompatível, quando validar, então a execução é impedida e o caminho/ID é informado. |
| AC-004 | Dado agente atribuído, quando preparar etapa, então o contrato fixado é carregado e required inputs/outputs ficam identificados. |
| AC-005 | Dado tipo `software`, quando selecionar `software-project`, então aplicabilidade é aceita; workflow incompatível é rejeitado. |
| AC-006 | Dado workflow válido, quando iniciar, então etapas, dependências e estado inicial são registrados uma única vez. |
| AC-007 | Dada predecessora não concluída, quando tentar iniciar etapa seguinte, então o avanço é bloqueado. |
| AC-008 | Dada transição válida, quando aplicada, então o estado do projeto é atualizado e registrado; transição inválida é rejeitada. |
| AC-009 | Dada tentativa, quando muda de estado, então etapa, tentativa, motivo e momento ficam consultáveis. |
| AC-010 | Dado required input ausente/inválido, quando validar, então a etapa não inicia e a lacuna é listada. |
| AC-011 | Dado artefato produzido, quando registrar, então ID, versão, tipo, produtor, fonte, estado e localização são preservados. |
| AC-012 | Dado gate, quando avaliar, então cada critério aponta para evidência/achado; ausência impede aprovação. |
| AC-013 | Dada aprovação obrigatória, quando alcançada, então execução pausa; somente decisão de autoridade registrada permite transição válida. |
| AC-014 | Dada transição relevante, quando ocorrer, então evento possui campos mínimos e correlação. |
| AC-015 | Dada execução, quando auditada, então é possível relacionar comandos, transições, gates, decisões e artefatos. |
| AC-016 | Dada falha, quando ocorrer, então causa segura é registrada, estado não avança e opções de correção/retomada são indicadas. |
| AC-017 | Dada execução elegível, quando retomar, então contexto/dependências são revalidados e nova tentativa preserva a anterior. |
| AC-018 | Dado cancelamento autorizado, quando confirmar, então estado terminal e motivo são registrados sem apagar histórico. |
| AC-019 | Dado ambiente local suportado, quando usar CLI, então capacidades Must são acessíveis sem interface gráfica. |
| AC-020 | Dado cenário essencial, quando executar sem credenciais/rede de provedor de IA, então ele pode chegar até seus gates humanos. |
| AC-021 | Dado projeto existente, quando consultar status, então nenhuma transição ou artefato é alterado. |
| AC-022 | Dado contexto classificado, quando recomendar workflow, então opções e justificativa são exibidas e exigem confirmação. |

## Não funcionais

| ID | Critério |
|---|---|
| AC-NF-001 | Uma amostra permite reconstruir causalidade por IDs e versões. |
| AC-NF-002 | Cenário de interrupção não deixa item parcial marcado `completed`. |
| AC-NF-003 | Varredura das evidências do cenário não encontra segredo ou dado pessoal de teste. |
| AC-NF-004 | Teste com operador identifica comando, resultado, erro e próxima ação sem consultar código. |
| AC-NF-005 | Cenário essencial funciona nos ambientes aprovados, ainda a definir. |
| AC-NF-006 | Falha simulada produz categoria, correlação e diagnóstico seguro. |
| AC-NF-007 | Versão incompatível é detectada antes do estágio consumidor. |
| AC-NF-008 | Critério será completado após Product/Operations definirem volume, ambiente e target. |

## Lacuna

Os critérios são testáveis como texto, exceto AC-NF-005/008, que permanecem
incompletos por falta de decisão e contexto operacional.
