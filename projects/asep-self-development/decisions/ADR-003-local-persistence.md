# ADR-003 — Estratégia de persistência local

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
Banco está fora do MVP; dados precisam ser legíveis, versionáveis e recuperáveis.
## Problema
Persistir definições, estado, artefatos e auditoria com integridade suficiente.
## Alternativas
Somente YAML; SQLite; YAML/Markdown + JSONL; estado apenas em memória.
## Decisão
YAML para definições/snapshots/manifests, Markdown para artefatos e JSONL para
logs/auditoria append-only. Escritas mutáveis usam temp+flush+atomic replace.
## Justificativa
Atende legibilidade e ausência de banco; JSONL é apropriado a eventos incrementais.
## Consequências
Single-writer/lock, schemas e recovery são obrigatórios. Consulta complexa é limitada.
## Riscos
Semântica de lock/replace varia por SO; edição manual e crash podem divergir dados.
Testar ambientes e reconciliar snapshot com `last_event_id`.
