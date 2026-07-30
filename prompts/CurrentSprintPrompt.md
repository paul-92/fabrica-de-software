# Prompt oficial da Sprint atual

**Sprint:** 8.6 — Architecture Hardening & Release Candidate RC1  
**Estado:** concluída localmente; publicação pendente

## Objetivo

Auditar arquitetura, código, documentação, testes, dependências, segurança e
Git, preparando migração e um candidato estável sem adicionar funcionalidade.

## Escopo entregue

- seis relatórios de auditoria;
- cobertura e estatísticas reproduzíveis;
- correção de `httpx2` para a dependência real `httpx`;
- fechamento explícito de conexões SQLite em fixtures;
- Migration Guide;
- Release Candidate RC1;
- documentação central sincronizada.

## Evidência

- 665 testes aprovados;
- 95% de cobertura;
- zero ciclos internos de imports;
- `pip check`, verificador do ambiente, `compileall`, links e diff check;
- nenhuma dependência proibida no Workflow Engine.

## Restrições

- nenhuma funcionalidade nova;
- nenhuma Fase 9 iniciada;
- nenhum novo Agent, Workflow, plugin, fila ou evento;
- nenhum commit, push ou tag automático.

## Gate de publicação

RC1 é tecnicamente válido localmente. Ainda exige revisão do diff acumulado,
commits/push, clone limpo ou CI, scanner de histórico e autorização de tag.

Referências:
[Sprint 8.6](../docs/phase-08/Sprint-8.6-Architecture-Hardening-RC1.md),
[RC1](../docs/releases/ReleaseCandidate_RC1.md),
[auditorias](../docs/audits/ArchitectureAudit.md) e
[NEXT_STEPS](../project/NEXT_STEPS.md).
