# Prompt oficial da Sprint atual

**Sprint:** 9.8 — Platform Hardening & Release Candidate 2
**Estado:** tecnicamente validada; revisão humana e publicação pendentes

## Objetivo

Consolidar a Fase 9 sem adicionar funcionalidades e preparar o RC2.

## Escopo entregue

- auditoria de arquitetura, código, dependências, segurança e testes;
- revisão de observabilidade, persistência, pipeline e API pública;
- consolidação de README, ArchitectureMap, Roadmap, Project State e índices;
- Release Notes e Migration Guide do RC2;
- revisão dos exemplos e gates completos.

## Evidência

- 794 testes aprovados com cobertura arredondada de 95%;
- 179 módulos Python e zero ciclos internos de import;
- três exemplos executados;
- `compileall`, `pip check`, links e `git diff --check` aprovados.

## Restrições

- nenhuma funcionalidade, agente, Tool, LLM, CLI, REST, Web ou scheduler;
- nenhuma mudança de API pública ou schema;
- nenhuma Fase 10;
- nenhum commit, push ou tag automático.

## Limites

O worktree acumulado ainda requer revisão humana e versionamento. Há 4.062
arquivos temporários de pytest rastreados no commit base. CI multiplataforma,
clone limpo, scanner de histórico e decisão sobre lockfile são gates de
publicação.

Referências:
[Sprint 9.8](../docs/phase-09/Sprint-9.8-Platform-Hardening-RC2.md),
[Release Candidate 2](../docs/releases/ReleaseCandidate2.md),
[Migration Guide RC2](../docs/migration/MigrationGuide-RC2.md) e
[NEXT_STEPS](../project/NEXT_STEPS.md).
