# Sistema ASEP

**Dono:** Orchestrator; **status:** ativo; **versão:** 0.1.0

Este é o documento central da plataforma. A ASEP recebe uma demanda, cria um registro de projeto, seleciona workflow e agentes via Registry, valida contratos e conduz estágios até encerramento verificável.

## Fluxo operacional

1. **Receber:** registrar origem, sponsor, problema, urgência, restrições, classificação de dados e autorização.
2. **Criar tarefas:** decompor o workflow em tarefas com ID, objetivo, entradas, saída, agente, dependências, gate e estado.
3. **Selecionar:** consultar capacidades, tipo de projeto, contrato, conflitos, disponibilidade e segregação de funções no Registry.
4. **Validar entradas:** schema, existência, versão, autorização, consistência e suficiência; lacunas viram bloqueio ou hipótese explícita conforme criticidade.
5. **Executar:** seguir lifecycle do agente e playbook aplicável, preservando eventos e artefatos.
6. **Revisar:** auto-review, revisão independente proporcional ao risco e quality gate com evidências.
7. **Aprovar:** pessoa com autoridade decide quando o contrato ou gate exigir; conflito de interesse impede autoaprovação.
8. **Encerrar tarefa:** confirmar saídas, handoff, eventos, decisões, pendências e atualização de estado.
9. **Tratar falhas:** classificar erro, preservar contexto, tentar correção segura, bloquear ou escalar; nunca ocultar falha.
10. **Solicitar decisão humana:** apresentar contexto, alternativas, impacto, recomendação, urgência e prazo.
11. **Armazenar:** artefatos específicos ficam no projeto; reutilizáveis aprovados em `artifacts/`; decisões em `decisions/`; aprendizado validado em `memory/`.
12. **Melhorar:** retrospectivas propõem mudanças; governança aprova; versão e catálogo são atualizados.

## Regras de composição

Contratos são interfaces; workflows são a ordem; agents definem comportamento; standards definem qualidade; knowledge informa decisões; playbooks orientam procedimento; Registry descobre componentes; Observability registra execução.

## Fonte de verdade

O projeto guarda o estado da iniciativa. Registry guarda catálogo, não estado de execução. Memory guarda apenas aprendizado global validado. Em conflito, prevalecem: autorização humana e lei → Core/Governance → contrato versionado → workflow → standards → playbook/knowledge.
