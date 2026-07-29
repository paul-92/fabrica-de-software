# Data Model

**ID:** ARCH-DAT-001 | **Versão:** 0.1.0 | **Status:** approved

## Entidades

| Entidade | Identidade e campos essenciais |
|---|---|
| Project | id, version, type, status, workflow_id, classification, approvals |
| WorkflowDefinition | id, version, stages, dependencies, conditions, gates |
| StageDefinition | id, mode=`sequential`, workflow, assigned_agents |
| WorkflowRun | id, project_id, definition_version, status, timestamps |
| StageRun | id, workflow_run_id, stage_id, attempt, status, inputs/outputs |
| AgentContract | id, version, required_inputs/outputs, gates, limits |
| ArtifactManifest | id, type, version, path, producer, sources, checksum, status |
| GateEvaluation | id, gate_id, criteria, evidence, findings, decision |
| ApprovalRequest | id, subject, required_authority, status, decision/conditions |
| DomainEvent | id, type, occurred_at, actor, trace/correlation, payload |
| ErrorRecord | code, category, retryable, safe_message, cause_reference |

## Relações

Project 1—N WorkflowRun; WorkflowRun 1—N StageRun; StageRun N—N ArtifactManifest
por referências; StageRun 1—N GateEvaluation; GateEvaluation 0—N ApprovalRequest;
todas as mudanças geram DomainEvent.

## Regras de dados

- IDs únicos dentro do projeto e imutáveis;
- datas UTC ISO 8601;
- enumerações fechadas e schema versionado;
- referências são relativas a uma raiz allowlisted;
- checksum SHA-256 identifica conteúdo, não autorização;
- payload de evento é minimizado;
- `extra=forbid` para declarativos executáveis; extensão futura usa campo versionado.

## Persistência

Definições e snapshots YAML, artefatos Markdown, manifests YAML e auditoria JSONL.
Não existe modelo relacional ou banco no MVP.
