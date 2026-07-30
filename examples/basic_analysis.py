"""Executa uma análise básica do workspace atual."""

from asep.pipeline import PipelineBuilder


engine = PipelineBuilder().build()
result = engine.execute(
    "Analise este projeto e explique sua arquitetura.",
    workspace=".",
)
print(result.summary)
