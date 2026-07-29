# Logging and Audit

**ID:** ARCH-LOG-001 | **Versão:** 0.1.0 | **Status:** approved

## Separação

**Logging** serve diagnóstico e pode ser rotacionado. **Audit Trail** registra
ações/decisões relevantes em append-only e é parte da evidência do projeto.

## Formatos

- terminal: Rich ou texto simples;
- log de arquivo: JSON Lines estruturado;
- auditoria: `.asep/audit/events.jsonl`;
- nenhum prompt integral, segredo ou conteúdo completo de artefato.

Campos mínimos: event_id/type, occurred_at UTC, actor_id/type declarado,
project_id, workflow/stage/agent run IDs quando aplicáveis, trace/correlation,
schema_version, classification, outcome e payload allowlisted.

## Consistência

Eventos de intenção e resultado distinguem operações. Audit append usa uma linha
por evento com flush; linha final truncada é detectada na abertura e gera recovery
finding. Estado guarda `last_event_id` para reconciliar snapshot e trilha.

## Redaction e retenção

Filtro central remove chaves conhecidas e impede logging de objetos não
serializáveis/allowlisted. Retenção exata permanece decisão humana; o MVP não
deleta automaticamente auditoria.

## Testes

Schema de eventos, correlação ponta a ponta, redaction, crash/truncamento, ordem,
Unicode e garantia de que consulta de status não emite evento mutável.
