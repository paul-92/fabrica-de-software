# Próximos passos

**Estado:** Fase 23 em andamento; Sprint 23.6 formalmente concluída

**Atualizado em:** 2026-08-12

**Dono:** Engenharia ASEP

## Objetivo imediato

Preservar o fechamento da vertical Runtime Branding e priorizar explicitamente
o próximo incremento da Fase 23. A conclusão da Sprint 23.6 não
encerra a Fase 23.

## Entrega consolidada da 23.6

- branding institucional canônico e persistência Memory/File/SQLite;
- query read-only com defaults e `GET /api/v1/branding`;
- App Shell com fallback build-time, runtime override e stale-response guard;
- tema, cores, favicon e metadata preservados fora do contrato runtime;
- administração completa somente por Application service e composição confiável;
- query/admin compartilham o mesmo repository do bundle;
- nenhuma rota HTTP de mutação ou UI administrativa.

## Continuidade da Fase 23

Produto deve definir o próximo objetivo, contratos e critérios de aceite. Não
inferir integração entre Session Memory, Agent Memory, `Run`,
`SequentialExecution` ou `ProjectExecution`. Auth/Authz e administração HTTP/UI
de branding são evoluções adiadas que exigem uma fronteira real de segurança;
não inferir usuário, role ou RBAC. Migração de YAML histórico e Intelligent
Orchestration continuam candidatos independentes, não requisitos implícitos.

## Riscos e preservação

- metadata, favicon, tema e cores do branding permanecem build-time/local;
- File Branding usa atomic replacement, sem prometer prevenção de lost update
  multiprocesso;
- alterações preexistentes fora do escopo não devem ser incluídas em commits;
- `WinError 5` em named pipes Python e `spawn EPERM` em workers Vite são
  limitações conhecidas de ambientes Windows restritos, não defeitos 23.6;
- publicação, CI remoto e commit continuam ações intencionais separadas.

## Responsáveis e gatilho

- **Produto:** priorizar o próximo incremento;
- **Arquitetura:** validar identidade e contratos públicos;
- **Engenharia:** implementar somente o slice aprovado;
- **Qualidade:** definir e executar seus gates.

O próximo slice começa apenas após objetivo, escopo, autoridade e critérios de
aceite explícitos.
