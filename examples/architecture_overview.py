"""Produz uma visão determinística da arquitetura documentada."""

from asep.pipeline import PipelineBuilder


result = PipelineBuilder().build().execute(
    "Leia a documentação e apresente uma visão da arquitetura.",
    workspace=".",
    options={
        "documentation_path": "architecture/ArchitectureMap.md",
        "read_path": "README.md",
    },
)
print(result.summary)
for artifact in result.artifacts:
    print(artifact["relative_path"])
