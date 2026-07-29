# Catálogo de Decisões Arquiteturais

**ID:** ARCH-DEC-001 | **Versão:** 0.1.0 | **Status:** approved  
**Dono:** Software Architect | **Data:** 2026-07-28

| ID | Decisão | Status | Evidência |
|---|---|---|---|
| ADR-001 | modular monolith local | accepted | [ADR-001](../decisions/ADR-001-architectural-style.md) |
| ADR-002 | camadas domain/application/ports/adapters/interfaces | accepted | [ADR-002](../decisions/ADR-002-source-structure.md) |
| ADR-003 | YAML/Markdown/JSONL em filesystem | accepted | [ADR-003](../decisions/ADR-003-local-persistence.md) |
| ADR-004 | workflow YAML validado por modelos versionados | accepted | [ADR-004](../decisions/ADR-004-workflow-format.md) |
| ADR-005 | Registry YAML com IDs únicos e referências resolvidas | accepted | [ADR-005](../decisions/ADR-005-registry-format-validation.md) |
| ADR-006 | snapshots atômicos e máquina de estados explícita | accepted | [ADR-006](../decisions/ADR-006-state-management.md) |
| ADR-007 | erro tipado, tentativa vinculada e retomada revalidada | accepted | [ADR-007](../decisions/ADR-007-failure-resumption.md) |
| ADR-008 | gates declarativos, evidência e decisão separadas | accepted | [ADR-008](../decisions/ADR-008-quality-gates.md) |
| ADR-009 | aprovação local explícita pelo CLI | accepted | [ADR-009](../decisions/ADR-009-human-approvals.md) |
| ADR-010 | logging diagnóstico + audit JSONL | accepted | [ADR-010](../decisions/ADR-010-logging-audit.md) |
| ADR-011 | Markdown por Jinja2 e manifesto de artefato | accepted | [ADR-011](../decisions/ADR-011-artifact-generation.md) |
| ADR-012 | pytest em pirâmide orientada a risco | accepted | [ADR-012](../decisions/ADR-012-testing-strategy.md) |
| ADR-013 | porta inativa para provedores futuros | accepted | [ADR-013](../decisions/ADR-013-ai-provider-extensibility.md) |
| ADR-014 | tailoring sequencial explícito para o piloto | accepted | [ADR-014](../decisions/ADR-014-sequential-execution-tailoring.md) |

## Avaliação da stack aprovada

| Item | Uso | Necessidade 0.1 | Alternativas consideradas |
|---|---|---|---|
| Python 3.12+ | runtime e stdlib (`json`, `logging`, `pathlib`) | obrigatório | outras linguagens exigiriam change request |
| Typer | comandos, parâmetros e help | obrigatório | `argparse` reduziria dependência, mas contraria stack aprovada |
| Pydantic | modelos, coerção controlada e erros de validação | obrigatório | dataclasses + validação manual aumentariam código |
| PyYAML | parsing YAML seguro | obrigatório | JSON/TOML não são formatos aprovados dos declarativos |
| Rich | tabelas, estados e erros legíveis | opcional na lógica; recomendado na CLI | saída texto simples deve permanecer testável |
| Jinja2 | templates Markdown com modo estrito | obrigatório para geração aprovada | concatenação manual é frágil |
| pytest | testes unitários, integração e aceitação | obrigatório no desenvolvimento | `unittest` é viável, mas menos alinhado à decisão |

Nenhuma biblioteca adicional é necessária no MVP. Locking, hashing, JSONL,
substituição atômica e logging usam a biblioteca padrão.

## Aprovação

Paulo Cesar é a autoridade de Arquitetura. O conjunto ADR-001–ADR-013 foi
aprovado em 2026-07-28 conforme `project.yaml`.
