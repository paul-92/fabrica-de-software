# Responsabilidades dos Módulos

**ID:** ARCH-MOD-001 | **Versão:** 0.1.0 | **Status:** approved

| Componente | Responsabilidade | Entrada → saída | Dependências/porta | Erros e limites | Teste principal |
|---|---|---|---|---|---|
| CLI | traduzir comandos e apresentar resultados | args → command/result | Application API | uso inválido; sem regra de negócio | CliRunner |
| Project Loader | localizar/validar projeto | path/id → Project | ProjectRepository | path escape, YAML inválido | fixtures |
| Registry Loader | carregar catálogos | roots → Registry | RegistryRepository | ID/path/versão inválidos | contrato |
| Contract Loader | resolver contrato do agente | agent/version → Contract | ContractRepository | required fields/referência | schema |
| Workflow Loader | resolver workflow | id/version → Workflow | WorkflowRepository | dependência/ciclo inválido | schema/grafo |
| Workflow Engine | calcular próxima etapa | workflow/state → transition proposal | State machine | predecessor/gate pendente | tabela de transições |
| Orchestrator | coordenar caso de uso | command/context → outcome | serviços/portas | conflito/bloqueio | integração |
| Agent Runtime | executar lifecycle do agente | task/contract/context → AgentResult | AgentPort | output inválido/falha | contrato |
| BA Adapter | gerar outputs determinísticos | facts/templates → Markdown drafts | ArtifactPort | dado ausente/template | golden files |
| Input Validator | validar required inputs | contract/artifacts → findings | repositories | incompatibilidade | matriz |
| Gate Evaluator | avaliar critérios/evidências | gate/evidence → evaluation | ArtifactPort | evidência ausente | tabela |
| Approval Manager | pausar/registrar decisão | request/decision → approval | State/Audit | autoridade declarada inválida | cenários |
| State Manager | aplicar transição atômica | current/event → new snapshot | StateRepository | transição inválida/conflito | propriedade/tabela |
| Artifact Manager | renderizar/registrar artefato | template/data → manifest/file | Jinja2/filesystem | path/template/colisão | golden/integration |
| Logging | diagnóstico seguro | event → record | logging | serialização/redaction | capture |
| Audit Trail | histórico append-only | domain event → JSONL | AuditSink | escrita parcial | replay |
| Error Handler | classificar e orientar | exception/finding → typed error | catálogo de erros | erro desconhecido | mapping |

## Limites

Nenhum módulo executa rede, autentica usuários, agenda paralelismo ou acessa banco.
Detalhes de método serão definidos no planejamento técnico, não neste documento.
