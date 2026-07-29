# Observability da ASEP

**Dono:** Operations | **Status:** especificação | **Versão:** 0.1.1

A observabilidade descreve como uma execução futura poderá ser diagnosticada,
medida e auditada. Esta versão não implementa coleta.

| Componente | Finalidade |
|---|---|
| [logging.md](logging.md) | eventos diagnósticos estruturados e sanitizados |
| [metrics.md](metrics.md) | indicadores de fluxo, qualidade e confiabilidade |
| [tracing.md](tracing.md) | causalidade entre tarefa, agente, gate e artefato |
| [audit.md](audit.md) | autoridade, versões, decisões, acessos e integridade |
| [status-model.md](status-model.md) | estados e transições permitidas |
| [event-catalog.yaml](event-catalog.yaml) | tipos e campos mínimos de evento |

Logs não contêm prompts integrais, segredos ou dados pessoais desnecessários.
Eventos operacionais não substituem artefatos, ADRs ou aprovações formais.
