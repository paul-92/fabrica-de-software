# Auditoria Git — RC1

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** bloqueio operacional aberto

## Estado observado

- branch: `feature/sprint-3-core-architecture`;
- HEAD: `863766f`;
- tracking: `origin/feature/sprint-3-core-architecture`;
- branch local: um commit à frente do tracking;
- tag existente: `v0.5.0`;
- branch `main` local também está à frente de `origin/main`;
- 603 arquivos rastreados antes de versionar o RC1;
- mudanças das Sprints 8.1–8.6 e migração estão não commitadas.

## Achados

Não há evidência de código perdido, mas o remoto **não é backup completo** do
estado atual. Diretórios temporários antigos apresentam `Permission denied` ao
serem enumerados; estão ignorados e não afetam a suíte com `--basetemp`.

Artefatos locais ignorados incluem `.coverage`, caches, `.venv`, `.asep`,
artifacts de runs, logs e diretórios QA. Não foram apagados.

## Classificação

O código é tecnicamente candidato, porém o RC1 não deve ser declarado
publicado enquanto:

1. o diff acumulado não for revisado;
2. commits intencionais não forem criados;
3. o branch não for enviado;
4. CI/clone limpo não confirmar os gates;
5. uma tag RC não for autorizada.

## Segurança Git

O scan atual não encontrou segredo em código/configuração rastreada. Recomenda-se
scanner de histórico antes do push final. Nenhum commit, push, reset, limpeza ou
tag foi executado por esta auditoria.

