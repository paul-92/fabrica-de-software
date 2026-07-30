# ExecutionPlan

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** contrato ativo

`ExecutionPlan` é a descrição imutável do trabalho pretendido. Ele contém
identidade determinística, objetivo, passos, estimativas, timestamp e metadata
JSON. Não contém objetos executáveis.

Cada `PlanStep` declara:

- identificador, descrição e capability obrigatória;
- Agent e Tool opcionais;
- dependências e prioridade;
- status inicial;
- custo e duração estimados;
- metadata JSON.

Os status são `pending`, `ready`, `completed`, `failed` e `skipped`. Nesta
Sprint o Planning Engine produz passos em `pending`; atualização de lifecycle
pertence a uma evolução futura.

Validações impedem IDs inválidos ou duplicados, auto-dependência, dependências
ausentes, ciclos, capabilities indisponíveis, limites de política e ordem
incompatível com o workflow. O modelo é serializável por Pydantic e não executa
qualquer ação.

Veja [Planning Engine](PlanningEngine.md).
