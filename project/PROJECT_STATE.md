# Estado atual da ASEP

**Atualizado em:** 2026-08-11
**Projeto:** AI Software Engineering Platform (ASEP)
**Versão do pacote:** 0.1.0
**Commit base avaliado:** `4b2fb1a363213495b2f100a9704036e9a8940a42`

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
- Fase 17 — Software Repair: blocos 17.1–17.4 concluídos.
- Fase 18 — Intelligent Engineering: blocos 18.1–18.4 concluídos.
- Fase 20 — Intelligent Integration: blocos 20.1–20.4 concluídos.
- Fase 21 — Application/API Layer: blocos 21.1–21.4 concluídos.
- Fase 22 — White-label Presentation Layer: concluída; gate frontend
  consolidado aprovado em 2026-08-11.
  Em 2026-08-11, 11 testes focados do contrato Application/API de Agents
passaram. A inspeção estática do frontend não encontrou imports para módulos
Python internos.

Durante o desenvolvimento da Presentation Layer, typecheck, lint e build
Next.js foram executados com sucesso em ambiente com Node/npm disponível.
Após a correção final de isolamento de `ThemeToggle.test.tsx`, seus 3 testes
focados passaram. O gate frontend consolidado completo ainda deve ser
reexecutado após essa última alteração antes do fechamento formal da Fase 22.

No PowerShell local utilizado para continuidade operacional, Node/npm não está
disponível no `PATH`; portanto esse ambiente específico não consegue executar
os gates frontend diretamente.

Consulte a [Fase 17](../docs/phase-17/software-repair.md) para o ciclo de
reparo, a [Fase 18](../docs/phase-18/intelligent-engineering.md) para a
composição inteligente controlada e a
[Fase 20](../docs/phase-20/intelligent-integration.md) para o fluxo de
conhecimento recuperado, Planning, engenharia e novo aprendizado, e a
[Fase 21](../docs/phase-21/application-api-layer.md) para a fachada de
Application e o adapter HTTP, e a
[Fase 22](../docs/phase-22/white-label-presentation-layer.md) para a camada
visual white-label, fronteiras, limitações e evidências. Consulte também a
[auditoria documental](../docs/audits/Phase-01-16-Documentation-Audit.md) para
a matriz histórica anterior.

## Git e ambiente desta fotografia

- branch: `feature/phase-10-business-engineering`;
- HEAD: `4b2fb1a363213495b2f100a9704036e9a8940a42`;
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

A camada Presentation em Next.js consome somente contratos HTTP públicos
versionados sob `/api/v1` e não importa módulos Python internos.

A camada Intelligence combina conhecimento recuperado com
`PlanningContext.memory` e consolida resultados de Planning e Autonomous
Engineering. Ela não acessa storage, não executa recomendações e não cria
retry.

## Evidência

As afirmações das Fases 15 e 16 foram verificadas em Orchestrator, seus modelos,
DeveloperAgent, Coordinator, Tools/workspace, Artifact Manager e Quality Gate
Engine; e nos testes QA de Coordination/Orchestrator e de Tool execution.

A auditoria documental não executou a suíte. O último gate histórico
documentado permanece o do RC2; ele não deve ser apresentado como resultado
novo desta revisão.

Em 2026-08-11, 11 testes focados do contrato Application/API de Agents
passaram. A inspeção estática do frontend não encontrou imports para módulos
internos.

Em 2026-08-11, o gate frontend consolidado da Fase 22 foi executado com Node.js
portátil em ambiente de usuário, sem necessidade de privilégios administrativos.

A suíte Vitest aprovou 25 arquivos e 117 testes, sem falhas. Typecheck e lint
foram aprovados. O build de produção Next.js foi concluído com sucesso e gerou
11 páginas estáticas, incluindo `/agents`, `/knowledge`, `/quality` e
`/planning`.

Com essas evidências, a Fase 22 está formalmente concluída.

## Limitações e pendências

- workflow e runtime permanecem síncronos;
- geração atual é determinística e dirigida pelo plano, não autônoma por IA;
- Intelligent Engineering exige conteúdo de substituição explícito e não
  possui IA externa ou retry próprio;
- Intelligent Integration reutiliza a Memory existente; `recommended_actions`
  e `should_retry` continuam informativos e não executáveis;
- Application/API expõe Intelligent Engineering sem construir infraestrutura;
- no Windows, o teste legado de multiprocessing pode falhar com `WinError 5`
  ao criar named pipe; essa limitação ambiental não é regressão da Fase 21;
- timeout do runtime não interrompe chamada bloqueada;
- publicação, CI remoto, scanner histórico e árvore limpa são gates
  operacionais separados;
- revisão humana desta atualização documental está pendente.

## Decisões essenciais

ADRs 016–029 continuam vigentes. ADR-030 registra a fronteira do Intelligent
Orchestrator; ADR-031, a geração controlada por Tools e workspace; e ADR-032,
a separação entre Software Repair e retry operacional.

## Leitura essencial

[Architecture Map](../docs/architecture/ArchitectureMap.md),
[Roadmap](../docs/architecture/Roadmap.md),
[Documentation Index](../docs/DocumentationIndex.md),
[Fase 15](../docs/phase-15/intelligent-orchestrator.md) e
[Fase 16](../docs/phase-16/software-generation-validation.md),
[Fase 17](../docs/phase-17/software-repair.md),
[Fase 18](../docs/phase-18/intelligent-engineering.md),
[Fase 20](../docs/phase-20/intelligent-integration.md) e
[Fase 21](../docs/phase-21/application-api-layer.md) e
[Fase 22](../docs/phase-22/white-label-presentation-layer.md).
