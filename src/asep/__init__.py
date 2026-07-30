"""AI Software Engineering Platform."""

from pathlib import Path
from typing import Any, Mapping

__version__ = "0.1.0"


def execute(
    goal: str,
    *,
    workspace: str | Path = ".",
    metadata: Mapping[str, Any] | None = None,
    options: Mapping[str, Any] | None = None,
):
    """Executa um objetivo pelo pipeline oficial com composição padrão."""
    from asep.pipeline import PipelineBuilder

    return PipelineBuilder().build().execute(
        goal,
        workspace=workspace,
        metadata=metadata,
        options=options,
    )


__all__ = ["__version__", "execute"]
