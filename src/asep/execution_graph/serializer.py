"""Serialização JSON determinística do ExecutionGraph."""

from __future__ import annotations

import json

from asep.execution_graph.models import ExecutionGraph


class ExecutionGraphSerializer:
    def serialize(self, graph: ExecutionGraph) -> str:
        return (
            json.dumps(
                graph.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
