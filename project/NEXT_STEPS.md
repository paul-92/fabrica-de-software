# Próximos passos

**Estado:** RC1 local após conclusão da Sprint 8.6

## Sprint atual

Sprint 8.6 — Architecture Hardening & RC1: auditorias e validações concluídas
localmente. A Fase 9 não está iniciada nem aprovada.

## Objetivo e escopo concluídos

Auditorias, correção de dependência de testes, fixtures SQLite sem warnings,
guia de migração e documento do Release Candidate.

## Critérios já atendidos

- 665 testes;
- cobertura de 95%;
- integração Run/Timeline/Metrics/Dashboard e Factory;
- seis auditorias, migração, RC1, glossário, história, mapa e índice;
- compileall e diff check.

## Pendências imediatas

1. revisar o diff acumulado da Fase 8/RC1;
2. criar commit intencional;
3. enviar o branch, incluindo o commit 7.5 ainda local;
4. confirmar CI/remoto;
5. fazer backup opcional dos runs/artifacts/logs locais;
6. clonar e validar na máquina nova;
7. executar scanner de histórico;
8. decidir lockfile;
9. aprovar formalmente a Fase 9 antes de qualquer implementação.

## Próximo planejamento

O Roadmap cita paralelismo, retry, cancelamento coordenado e Dashboard MVP, mas
não atribui número/ordem. Não implementar nenhum deles sem prompt e decisão.

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
[Sprint 8.6](../docs/phase-08/Sprint-8.6-Architecture-Hardening-RC1.md) e
[RC1](../docs/releases/ReleaseCandidate_RC1.md).
