# ADR-021 — Persistir snapshots, não objetos vivos de workflow

**Status:** aceito localmente  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

Run e Timeline não preservam juntos definição, etapas, métricas e resultado do
workflow. Persistir `WorkflowContext` ou Steps concretas acoplaria storage a
código executável e criaria riscos de segurança e compatibilidade.

## Decisão

Persistir um `WorkflowSnapshot` imutável, estrito e JSON-safe. Usar identidade
própria para preservar vários registros por Workflow/Run. Integrar no
Orchestrator por porta opcional; manter o Engine sem dependência de storage.
Fornecer backends memory, file e SQLite via Factory.

## Alternativas

- ampliar `Run` com todos os dados;
- serializar Definition, Steps ou Context integralmente;
- fazer o Engine salvar diretamente;
- persistir apenas no SQLite;
- usar snapshots neutros por uma porta.

## Consequências

- backends intercambiáveis;
- histórico preservado por novos IDs;
- Timeline referenciada sem duplicação;
- sem retomada automática;
- update explícito não cria revisão;
- novo arquivo configurável e tabela SQLite.

## Evolução

Retomada, retenção, migrations, concorrência e exposição por API exigem casos de
uso e decisões próprios. A Fase 9 não é iniciada por este ADR.

