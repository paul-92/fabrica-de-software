# Próximos passos

**Estado:** Sprint 10.1 implementada; validação final e publicação pendentes

## Sprint atual

Sprint 10.1 — Project Analyzer: análise determinística de estrutura,
tecnologias, arquitetura, dependências e estatísticas.

## Objetivo e escopo concluídos

Módulo `asep.project_analysis` isolado do Runtime, com fachada pública,
detectores heurísticos, modelos imutáveis, testes e documentação.

## Critérios já atendidos

- fachada `ProjectAnalyzer` e modelo `ProjectAnalysis`;
- scanner configurável e caminhos relativos;
- dez linguagens e nove frameworks;
- package managers, entrypoints e dependências diretas;
- arquitetura heurística e estatísticas;
- cobertura específica do módulo superior a 95%.

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

Não iniciar a Sprint 10.2 sem autorização explícita. Integração do Analyzer com
Runtime, LLM, embeddings, geração, revisão e refatoração automáticas permanecem
fora do escopo.

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
