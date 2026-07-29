# Tracing

**Dono:** Operations | **Status:** especificação | **Versão:** 0.1.1

`trace_id` representa a execução ponta a ponta. `project_id`, `workflow_run_id`,
`stage_run_id`, `task_id`, `agent_run_id`, `approval_id`, `gate_evaluation_id`
e `artifact_id` reconstroem causalidade sem copiar conteúdo dos artefatos.

Cada etapa cria span com início, fim, status, versões e relações para sequência ou
paralelismo. Retorno preserva o trace; retry incrementa `attempt` e aponta para a
tentativa anterior. Operação externa registra apenas metadados permitidos.

Uma amostra deve permitir seguir demanda → agente → gate → artefato → handoff,
incluindo loops de correção e aprovações, sem expor dados classificados.
