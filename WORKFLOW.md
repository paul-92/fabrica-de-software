# Visão Geral dos Workflows

**Dono:** Orchestrator  
**Status:** ativo  
**Versão:** 0.1.0

Workflows definem ordem, paralelismo, condições, retornos, gates, aprovações, bloqueios, cancelamento e retomada. O ciclo de vida canônico está em [core/LIFECYCLE.md](core/LIFECYCLE.md); os workflows executáveis declarativamente ficam em `workflows/*.yaml` e o catálogo em [registry/workflows.yaml](registry/workflows.yaml).

## Regras

1. Toda execução tem projeto, workflow, versão, responsável e estado.
2. Etapa só inicia com dependências e entradas validadas.
3. Paralelismo exige independência explícita e estratégia de reconciliação.
4. Gate exige evidência real; ausência nunca equivale a aprovação.
5. Retorno para correção preserva histórico e motivo.
6. Aprovação humana registra solicitante, autoridade, decisão, data e condições.
7. Bloqueio possui causa, dono e gatilho de retomada.
8. Cancelamento preserva artefatos, auditoria e obrigações de retenção.

## Estados

`planned`, `ready`, `running`, `blocked`, `failed`, `awaiting_approval`, `completed`, `cancelled`. Transições válidas estão em [observability/status-model.md](observability/status-model.md).
