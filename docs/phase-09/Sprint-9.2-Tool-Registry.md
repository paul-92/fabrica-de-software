# Sprint 9.2 — Tool Contracts & Tool Registry

**Público:** engenharia, arquitetura e QA  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementada localmente

## Objetivo

Criar a fronteira oficial para capacidades reutilizáveis, impedindo que agentes
precisem conhecer filesystem, subprocesso ou implementações concretas.

## Entregas

- contratos e modelos imutáveis de Tools;
- Registry em memória determinístico;
- validator, policy, exceções e serviço de execução;
- Timeline e métricas específicas;
- isolamento central de workspace;
- `ReadFileTool`, `ListDirectoryTool`, `SearchFilesTool`,
  `ReadDocumentationTool` e `RunTestsTool`;
- porta opcional de Tools no Agent Runtime;
- testes unitários e integrados;
- documentação e ADR-023.

## Decisões

Tools são independentes de Workflow, agentes e providers. Registry apenas
localiza. O serviço coordena validação, execução e observabilidade. A API
permanece síncrona. Não há Tool de escrita nem execução arbitrária.

## Evidências

Testes de Registry, execução e Tools exercitam capability, erro, retry, timeout,
Timeline, métricas, traversal, workspace, symlink, documentação e comando fixo
de testes.

## Riscos e limitações

- timeout observacional para Tools Python;
- estado e métricas locais ao processo;
- ausência de autorização por identidade de agente;
- busca simples, sem índice;
- artefatos `.pytest-tmp-sprint91-*` foram rastreados no commit anterior e
  aparecem deletados no worktree; não pertencem a esta Sprint.

## Checklist

- [x] contratos, Registry, validator, policy e serviço;
- [x] cinco Tools iniciais;
- [x] Timeline, métricas e Agent Runtime;
- [x] segurança e testes;
- [x] documentação e ADR;
- [ ] revisão humana e commit autorizados.

## Próxima ação

Responsável: mantenedor autorizado. Gatilho: gates técnicos verdes e resolução
dos temporários rastreados. A Sprint 9.3 não foi iniciada.

## Referências

[Tool Architecture](../tools/ToolArchitecture.md) e
[ADR-023](../adr/ADR-023-tool-registry.md).

