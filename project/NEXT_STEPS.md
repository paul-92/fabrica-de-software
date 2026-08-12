# Próximos passos

**Estado:** Fase 23 em andamento; Sprint 23.5 formalmente concluída

**Atualizado em:** 2026-08-12

**Dono:** Engenharia ASEP

## Objetivo imediato

Preservar o fechamento da vertical Advanced Knowledge Queries e priorizar
explicitamente o próximo incremento da Fase 23. A conclusão da Sprint 23.5 não
encerra a Fase 23.

## Entrega consolidada da 23.5

- query read-only separada do command contract e com a mesma fonte operacional;
- busca substring normalizada, kind, ordem total e keyset pagination;
- autorização Project → Session antes de qualquer consulta;
- endpoint aditivo `/api/v1/projects/{project}/sessions/{session}/memory/search`;
- GET/POST legado de `/memory` preservados;
- `/knowledge` com filtros, carregar mais, retry e proteção contra stale response;
- paridade InMemory/SQLite; backend `file` continua InMemory para session memory;
- nenhum score, ranking, embedding, busca global ou `total_count`.

## Continuidade da Fase 23

Produto deve definir o próximo objetivo, contratos e critérios de aceite. Não
inferir integração entre Session Memory, Agent Memory, `Run`,
`SequentialExecution` ou `ProjectExecution`. Branding dinâmico, migração de
YAML histórico e Intelligent Orchestration continuam candidatos independentes,
não requisitos implícitos.

## Riscos e preservação

- cursor é opaco e validado, mas não assinado nem criptografado;
- paginação keyset não representa snapshot histórico transacional;
- alterações preexistentes fora do escopo não devem ser incluídas em commits;
- `WinError 5` em named pipes Python e `spawn EPERM` em workers Vite são
  limitações conhecidas de ambientes Windows restritos, não defeitos 23.5;
- publicação, CI remoto e commit continuam ações intencionais separadas.

## Responsáveis e gatilho

- **Produto:** priorizar o próximo incremento;
- **Arquitetura:** validar identidade e contratos públicos;
- **Engenharia:** implementar somente o slice aprovado;
- **Qualidade:** definir e executar seus gates.

O próximo slice começa apenas após objetivo, escopo, autoridade e critérios de
aceite explícitos.
