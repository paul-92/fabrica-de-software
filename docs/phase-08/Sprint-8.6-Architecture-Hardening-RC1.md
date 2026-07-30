# Sprint 8.6 — Architecture Hardening & RC1

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída localmente

## Objetivo

Auditar e consolidar a plataforma sem adicionar comportamento funcional.

## Trabalho realizado

- auditorias de arquitetura, código, testes, dependências, segurança e Git;
- cobertura integral da suíte;
- correção da dependência de testes `httpx2` para `httpx`;
- fechamento explícito de conexões SQLite em fixtures;
- guia de migração e documento RC1;
- sincronização de estado, Roadmap, mapa e índices.

## Evidência

- 665 testes;
- cobertura de 95%;
- zero ciclos internos de imports;
- 67 links Markdown validados antes dos novos documentos;
- ambiente Python 3.14.4/Windows 11;
- `pip check`, `compileall` e diff check aprovados.

## Gate

Tecnicamente apto como candidato local. Publicação permanece condicionada a
commit/push, clone limpo, CI e scanner de histórico.

## Limitações

Nenhuma capacidade da Fase 9 foi iniciada. Dívidas e riscos estão nos
[relatórios de auditoria](../audits/ArchitectureAudit.md).

## ADR

Nenhum ADR foi criado: não houve nova decisão arquitetural, apenas hardening de
testes, dependências e documentação.

