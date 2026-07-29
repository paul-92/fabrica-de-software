# Backlog ASEP 1.0

| Épico | Funcionalidade | Descrição | Prioridade | Dependências | Critérios de aceite | Status | Evidência esperada |
|---|---|---|---|---|---|---|---|
| Fundação | Modelo documental | Core, organização e navegação | Must | nenhuma | links e auditoria válidos | done | relatório |
| Catálogo | Registry | descoberta de componentes | Must | fundação | caminhos e IDs válidos | done | validação YAML |
| Interfaces | Contratos | contratos de 15 agentes | Must | catálogo | schemas e encadeamento válidos | done | matriz de contratos |
| Fluxo | Workflows | sete tipos declarativos | Must | gates/contratos | agentes e gates existentes | done | validação cruzada |
| Execução | Schema formal | JSON Schema/YAML Schema versionado | Must | workflows | exemplos passam/falham corretamente | planned | testes |
| Orchestrator | Estado mínimo | tarefas, transições e aprovações | Must | schema, ADR | cenários de bloqueio/retomada passam | planned | testes de aceitação |
| Runtime | Lifecycle | execução isolada por contrato | Must | orchestrator | lifecycle auditável | planned | traces |
| Segurança | Threat model | riscos do Runtime | Must | arquitetura | controles e riscos aprovados | planned | threat model |
| Piloto | Self-development | executar ASEP sobre si | Must | runtime mínimo | métricas e retrospectiva | planned | relatório piloto |
| Release | 1.0 | pacote utilizável e handover | Must | piloto | gates de release e aceite | planned | release report |
