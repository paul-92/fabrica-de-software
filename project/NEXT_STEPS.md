# Próximos passos

**Estado:** Sprint 9.8 validada tecnicamente; RC2 pendente de aceite operacional

## Sprint atual

Sprint 9.8 — Platform Hardening & Release Candidate 2: auditoria, consolidação
documental e gates técnicos concluídos localmente.

## Objetivo e escopo concluídos

Arquitetura da Fase 9 auditada sem ciclos; código, dependências, segurança,
persistência, observabilidade, API e exemplos revisados. Release Notes,
Migration Guide e diagrama oficial do RC2 foram produzidos.

## Critérios já atendidos

- 794 testes aprovados com 95% de cobertura;
- 179 módulos e zero ciclos internos de import;
- três exemplos aprovados;
- `compileall`, `pip check` e `git diff --check` aprovados;
- documentação principal alinhada ao RC2.

## Pendências imediatas

1. remover intencionalmente do índice os 4.062 arquivos
   `.pytest-tmp-sprint91-*` rastreados no commit base;
2. revisar o diff acumulado das Sprints 9.2–9.8;
3. criar commit intencional somente após autorização;
4. enviar o branch e confirmar CI/remoto;
5. validar em clone limpo/CI multiplataforma e executar scanner de histórico;
6. avaliar e publicar formalmente o RC2;
7. decidir sobre lockfile antes do release estável.

## Próximo planejamento

Não iniciar a Fase 10 sem autorização explícita. CLI/REST/Web específicos do
pipeline, LLM, persistência do pipeline, paralelismo e scheduler exigem
requisito e decisão próprios.

## Validação

```text
python scripts/verify_environment.py
python -m pytest -v
python -m compileall src tests
git diff --check
git status --short
```

## Riscos e dependências

- perda de mudanças se migrar antes do push;
- dados ignorados não seguem pelo Git;
- resolução futura de dependências pode variar por ausência de lockfile;
- Python 3.12+ deve ser usado; 3.14.4 é o ambiente comprovado.

Referências: [Roadmap](../docs/architecture/Roadmap.md),
[prompt oficial](../prompts/CurrentSprintPrompt.md) e
[Sprint 9.8](../docs/phase-09/Sprint-9.8-Platform-Hardening-RC2.md),
[Release Candidate 2](../docs/releases/ReleaseCandidate2.md) e
[Migration Guide RC2](../docs/migration/MigrationGuide-RC2.md).
