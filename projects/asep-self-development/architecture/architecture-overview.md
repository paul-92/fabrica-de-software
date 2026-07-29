# Architecture Overview — ASEP CLI 0.1

**ID:** ARCH-OV-001 | **Versão:** 0.1.0 | **Status:** approved  
**Dono:** Software Architect | **Data:** 2026-07-28

## Decisão resumida

A versão 0.1 será um **modular monolith local**, executado em um único processo
Python e distribuído como aplicação CLI. Módulos separam domínio, casos de uso,
portas e adaptadores, mas são implantados e versionados juntos.

## Drivers

- executar um fluxo ASEP completo, sequencial e auditável;
- validar YAML antes de mudar estado;
- preservar estado e retomada sem banco de dados;
- bloquear gates e aprovações sem evidência;
- gerar Markdown determinístico;
- operar sem Web, autenticação, multiusuário, paralelismo ou IA externa;
- manter módulos testáveis sem acoplá-los à CLI ou ao filesystem.

## Estrutura lógica

```text
CLI (Typer/Rich)
  → Application Services / Orchestrator
    → Domain (workflow, state, gates, approvals, errors)
      → Ports
        → YAML Registry/Workflow/Contract loaders
        → File State / JSONL Audit / Markdown Artifacts
        → Business Analyst Adapter
```

O domínio não importa Typer, PyYAML, Rich, Jinja2 nem APIs de filesystem. Casos de
uso coordenam portas; adaptadores implementam tecnologia.

## Persistência

- YAML: projetos, Registry, contratos, workflows e snapshots de estado;
- Markdown: artefatos humanos;
- JSON Lines: trilha de auditoria append-only;
- logs diagnósticos: saída estruturada para arquivo/terminal;
- escrita mutável: arquivo temporário, flush e substituição atômica;
- single-writer: lock local por projeto, sem promessa multiusuário.

## Fluxo mínimo

`init → validate → start → run-next → gate → approve/reject → resume/cancel → status`.
O Business Analyst Adapter não inventa requisitos: valida entradas e gera
artefatos Markdown a partir de dados declarados/templates.

## Limites

Não há daemon, API, container obrigatório, banco, fila, plugin dinâmico, execução
paralela, autenticação ou chamada externa de IA. Extensões futuras dependem de
portas estáveis e novos ADRs.

## Evidência

ADRs 001–013, modelos de componente/estado/dados, matriz de rastreabilidade e
review em `reports/architecture-review.md`.
