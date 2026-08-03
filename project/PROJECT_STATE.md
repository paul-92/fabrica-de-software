# Estado atual da ASEP

**Atualizado em:** 2026-08-03
**Projeto:** AI Software Engineering Platform (ASEP)
**Versão do pacote:** 0.1.0
**Commit avaliado:** `bd138b26c0e37b5c4551b70925f8f5573dd49f11`

## Estado de entrega

As Fases 6–9 permanecem concluídas conforme seus documentos e RCs. A linha de
Business Engineering e execução avançou por implementação e testes:

- Fase 10 — Business Engineering: implementada;
- Fase 11 — Business Engineering → Planning: implementada;
- Fase 12 — Planning → Agent Coordination: implementada;
- Fase 13 — Coordination → Agent Runtime: implementada;
- Fase 14 — DeveloperAgent → Tool Execution: implementada;
- Fase 15 — Intelligent Orchestrator: concluída;
- Fase 16 — Software Generation & Validation Pipeline: concluída.

Não há Fase 17 definida. Consulte a
[auditoria documental](../docs/audits/Phase-01-16-Documentation-Audit.md) para
a matriz, evidências e limitações.

## Git e ambiente desta fotografia

- branch: `feature/phase-10-business-engineering`;
- HEAD: `bd138b26c0e37b5c4551b70925f8f5573dd49f11`;
- remoto correspondente: `origin/feature/phase-10-business-engineering`;
- há 4.062 remoções rastreadas em `.pytest-tmp-sprint91-*`, preexistentes e
  fora do escopo da auditoria documental.

## Arquitetura atual

A plataforma é um monólito modular Python. Business Engineering produz um
`ProjectBlueprint`; adapters levam o resultado ao Planning e à Coordination;
o Agent Runtime executa agentes registrados; `DeveloperAgent` solicita efeitos
por Tools; artefatos e Quality Gates permanecem serviços separados. O
`IntelligentOrchestratorService` consolida esse caminho e devolve resultado
tipado.

Persistência continua disponível em memory, arquivo JSON e SQLite. O núcleo de
workflow e o pipeline inteligente são síncronos. Providers, exporters,
Timeline, métricas, Dashboard, memória, recovery e Project Analyzer preservam
as fronteiras documentadas nos ADRs existentes.

## Evidência

As afirmações das Fases 15 e 16 foram verificadas em Orchestrator, seus modelos,
DeveloperAgent, Coordinator, Tools/workspace, Artifact Manager e Quality Gate
Engine; e nos testes QA de Coordination/Orchestrator e de Tool execution.

A auditoria documental não executou a suíte. O último gate histórico
documentado permanece o do RC2; ele não deve ser apresentado como resultado
novo desta revisão.

## Limitações e pendências

- workflow e runtime permanecem síncronos;
- geração atual é determinística e dirigida pelo plano, não autônoma por IA;
- timeout do runtime não interrompe chamada bloqueada;
- publicação, CI remoto, scanner histórico e árvore limpa são gates
  operacionais separados;
- revisão humana desta atualização documental está pendente.

## Decisões essenciais

ADRs 016–029 continuam vigentes. ADR-030 registra a fronteira do Intelligent
Orchestrator e ADR-031, a geração controlada por Tools e workspace.

## Leitura essencial

[Architecture Map](../docs/architecture/ArchitectureMap.md),
[Roadmap](../docs/architecture/Roadmap.md),
[Documentation Index](../docs/DocumentationIndex.md),
[Fase 15](../docs/phase-15/intelligent-orchestrator.md) e
[Fase 16](../docs/phase-16/software-generation-validation.md).
