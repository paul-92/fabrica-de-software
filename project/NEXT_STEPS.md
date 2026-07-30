# Próximos passos

**Estado:** Sprint 9.1 implementada localmente

## Sprint atual

Sprint 9.1 — Intelligent Agent Runtime: implementação, integração e
documentação concluídas localmente. A Sprint 9.2 não foi iniciada.

## Objetivo e escopo concluídos

Runtime síncrono com Registry, policy, validator, Timeline, métricas,
idempotência local e integração ao Workflow Engine por adapter.

## Critérios já atendidos

- runtime e contratos testados sem provider real;
- compatibilidade do Business Analyst e do caminho direto;
- eventos e métricas terminais;
- proteção de metadata sensível;
- documentação e ADR-022.

## Pendências imediatas

1. executar e revisar os gates finais da Sprint 9.1;
2. revisar o diff acumulado da Fase 8/RC1 e Fase 9.1;
3. criar commit intencional somente após autorização;
4. enviar o branch e confirmar CI/remoto;
5. executar scanner de histórico;
6. aprovar formalmente a Sprint 9.2 antes de qualquer implementação.

## Próximo planejamento

Não iniciar a Sprint 9.2. Evoluções possíveis incluem cancelamento cooperativo,
idempotência durável e composição do coletor de métricas, mas exigem prompt e
decisão próprios.

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
[Sprint 9.1](../docs/phase-09/Sprint-9.1-Intelligent-Agent-Runtime.md) e
[Agent Runtime](../docs/agents/AgentRuntime.md).
