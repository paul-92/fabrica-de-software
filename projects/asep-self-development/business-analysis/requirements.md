# Catálogo mestre de requisitos

**ID:** BA-REQ-001 | **Versão:** 0.1.2 | **Status:** baseline aprovada; `QG-ANALYSIS` approved  
**Dono:** Business Analyst | **Data:** 2026-07-28

Este catálogo evita duplicação: a formulação detalhada está em
[functional-requirements.md](functional-requirements.md) e
[non-functional-requirements.md](non-functional-requirements.md).

## Requisitos funcionais

| ID | Capacidade | Prioridade proposta | Critério |
|---|---|---|---|
| FR-001 | criar ou abrir projeto | Must | AC-001 |
| FR-002 | carregar Registry | Must | AC-002 |
| FR-003 | validar referências declarativas | Must | AC-003 |
| FR-004 | carregar contratos | Must | AC-004 |
| FR-005 | selecionar e validar workflow | Must | AC-005 |
| FR-006 | instanciar execução e etapas | Must | AC-006 |
| FR-007 | executar etapas sequencialmente | Must | AC-007 |
| FR-008 | manter estado do projeto | Must | AC-008 |
| FR-009 | manter estado das etapas/tentativas | Must | AC-009 |
| FR-010 | validar entradas | Must | AC-010 |
| FR-011 | registrar artefatos | Must | AC-011 |
| FR-012 | avaliar quality gates | Must | AC-012 |
| FR-013 | solicitar/registrar aprovação humana | Must | AC-013 |
| FR-014 | emitir logs/eventos | Must | AC-014 |
| FR-015 | preservar auditoria | Must | AC-015 |
| FR-016 | tratar falhas | Must | AC-016 |
| FR-017 | retomar execução | Must | AC-017 |
| FR-018 | cancelar execução | Must | AC-018 |
| FR-019 | operar por CLI local | Must | AC-019 |
| FR-020 | operar sem provedor externo de IA | Must | AC-020 |
| FR-021 | inspecionar estado sem alterá-lo | Should | AC-021 |
| FR-022 | recomendar workflow automaticamente | Could | AC-022 |

## Requisitos não funcionais

| ID | Qualidade | Prioridade | Critério |
|---|---|---|---|
| NFR-001 | rastreabilidade | Must | AC-NF-001 |
| NFR-002 | integridade de estado | Must | AC-NF-002 |
| NFR-003 | segurança de dados | Must | AC-NF-003 |
| NFR-004 | usabilidade da CLI | Must | AC-NF-004 |
| NFR-005 | portabilidade local | Should | AC-NF-005 |
| NFR-006 | diagnosticabilidade | Must | AC-NF-006 |
| NFR-007 | compatibilidade versionada | Must | AC-NF-007 |
| NFR-008 | desempenho/capacidade | pendente | AC-NF-008 |

## Baseline

Os itens `Must` que implementam os componentes explicitamente aprovados compõem a
baseline `0.1`. Itens `Should` e `Could` permanecem candidatos. O
`QG-ANALYSIS` foi aprovado pelo owner registrado após aceite do Product Owner.
