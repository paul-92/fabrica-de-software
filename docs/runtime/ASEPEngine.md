# ASEP Engine

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** API pública

`ASEPEngine` é a fachada oficial para executar um objetivo sem expor Runtime,
Planner, Coordinator ou infraestrutura.

```python
from asep.pipeline import PipelineBuilder

engine = PipelineBuilder().build()
result = engine.execute(
    "Analise este projeto e explique sua arquitetura.",
    workspace=".",
)
print(result.summary)
```

A forma curta é:

```python
import asep

result = asep.execute("Resuma este diretório.", workspace=".")
```

`execute` recebe objetivo, workspace, metadata e options. O retorno
`GoalResult` contém status, resumo, etapas, Timeline, métricas, duração,
artefatos e metadata sanitizada.

A composição padrão é local e em memória. Aplicações futuras poderão construir
outra composição e reutilizar a mesma fachada.

Veja [Execution Pipeline](ExecutionPipeline.md) e
[Getting Started](../examples/GettingStarted.md).
