# Orchestrator Design

**ID:** ARCH-ORC-001 | **Versão:** 0.1.0 | **Status:** approved

## Responsabilidade

Implementar casos de uso que coordenam loaders, Engine, Runtime, gates, approvals,
estado, artefatos e eventos. Não contém regras especializadas de análise nem
implementa diretamente persistência.

## Casos de uso

- `InitializeProject`;
- `ValidateProject`;
- `StartWorkflow`;
- `RunNextStage`;
- `EvaluateGate`;
- `Request/RecordApproval`;
- `ResumeExecution`;
- `CancelExecution`;
- `GetStatus`.

## Sequência de comando mutável

Carregar snapshot → validar comando e versões → adquirir lock → recalcular
precondições → coordenar componentes → preparar mudança → persistir atomicamente
→ emitir auditoria → liberar lock → retornar outcome.

## Entradas e saídas

Recebe comandos tipados com project/run IDs e ator declarado. Retorna `Outcome`
com estado, artefatos, eventos, findings e próxima ação. Nunca retorna somente
boolean nem propaga traceback ao operador.

## Limites

Não cria requisitos, escolhe arquitetura, executa vários estágios, autoaprova
gate, chama IA ou mantém estado global oculto.

## Critérios de teste

Testes de caso de uso verificam ordem das portas, ausência de efeitos em falha de
validação, idempotência de comando repetido, bloqueio por gate, retomada e
cancelamento. Integração usa filesystem temporário.
