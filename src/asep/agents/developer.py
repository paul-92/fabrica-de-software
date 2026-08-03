"""Agente determinístico de demonstração do pipeline E2E."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from asep.agents.contracts import (
    AgentCapability,
    AgentId,
    AgentMetadata,
    AgentRequest,
)
from asep.execution.models import (
    AgentContext,
    AgentResult,
    AgentResultStatus,
    ArtifactDraft,
)
from asep.tools.contracts import ToolExecutor
from asep.tools.models import (
    ToolCapability,
    ToolExecutionStatus,
    ToolId,
    ToolRequest,
)


class DeveloperAgent:
    metadata = AgentMetadata(
        id=AgentId(value="developer"),
        name="Deterministic Developer",
        description=(
            "Executa Tools determinísticas de análise, escrita e testes "
            "sem IA ou inferência."
        ),
        version="1.0.0",
        capabilities=tuple(
            AgentCapability(id=item)
            for item in (
                "directory",
                "search",
                "read_file",
                "documentation",
                "write_file",
                "test",
            )
        ),
    )

    def __init__(self, tool_executor: ToolExecutor) -> None:
        self._tools = tool_executor

    def execute(
        self,
        request: AgentRequest,
        context: AgentContext,
    ) -> AgentResult:
        step = request.inputs.get("plan_step", {})

        if not isinstance(step, Mapping):
            return self._failed(
                context,
                "PlanStep ausente.",
            )

        capability = str(
            step.get(
                "required_capability",
                "",
            )
        )

        tool_data = step.get("tool_id")

        tool_id = (
            tool_data.get("value")
            if isinstance(tool_data, Mapping)
            else tool_data
        )

        workspace = request.metadata.get("workspace")

        if not isinstance(tool_id, str) or not isinstance(
            workspace,
            str,
        ):
            return self._failed(
                context,
                "Tool ou workspace ausente.",
            )

        options = request.metadata.get(
            "options",
            {},
        )

        if not isinstance(options, Mapping):
            options = {}

        step_metadata = step.get(
            "metadata",
            {},
        )

        if not isinstance(step_metadata, Mapping):
            step_metadata = {}

        merged_options = {
            **dict(options),
            **dict(step_metadata),
        }

        payload = self._payload(
            capability,
            merged_options,
        )

        tool_result = self._tools.execute(
            ToolRequest(
                execution_id=f"{request.request_id}-tool",
                tool_id=ToolId(
                    value=tool_id,
                ),
                capability=ToolCapability(
                    id=capability,
                ),
                workspace=Path(workspace),
                payload=payload,
                metadata={
                    "agent_id": context.agent_id,
                    "stage_id": context.stage_id,
                },
                workflow_execution_id=context.run_id,
            )
        )

        if tool_result.status is not ToolExecutionStatus.SUCCEEDED:
            return self._failed(
                context,
                (
                    tool_result.error.message
                    if tool_result.error
                    else "Tool falhou."
                ),
            )

        output = tool_result.model_dump(
            mode="json"
        )["output"]

        return AgentResult(
            status=AgentResultStatus.COMPLETED,
            agent_id=context.agent_id,
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=context.started_at,
            finished_at=tool_result.completed_at,
            artifacts=[
                ArtifactDraft(
                    relative_path=(
                        f"pipeline/{context.stage_id}.json"
                    ),
                    type="json",
                    content=json.dumps(
                        output,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                )
            ],
            messages=[
                (
                    f"{context.stage_id}: "
                    f"Tool {tool_id} executada com sucesso."
                )
            ],
            metadata={
                "tool_id": tool_id,
                "capability": capability,
            },
        )

    @staticmethod
    def _payload(
        capability: str,
        options: Mapping,
    ) -> dict[str, object]:
        if capability == "directory":
            return {
                "path": str(
                    options.get(
                        "directory",
                        ".",
                    )
                )
            }

        if capability == "search":
            return {
                "path": str(
                    options.get(
                        "directory",
                        ".",
                    )
                ),
                "extension": str(
                    options.get(
                        "extension",
                        ".py",
                    )
                ),
            }

        if capability == "read_file":
            return {
                "path": str(
                    options.get(
                        "read_path",
                        "README.md",
                    )
                )
            }

        if capability == "documentation":
            return {
                "path": str(
                    options.get(
                        "documentation_path",
                        "architecture/ArchitectureMap.md",
                    )
                )
            }

        if capability == "write_file":
            return {
                "path": str(
                    options.get(
                        "write_path",
                        "src/main.py",
                    )
                ),
                "content": str(
                    options.get(
                        "content",
                        "",
                    )
                ),
                "overwrite": bool(
                    options.get(
                        "overwrite",
                        False,
                    )
                ),
            }

        if capability == "test":
            paths = options.get(
                "test_paths",
                ["tests"],
            )

            if not isinstance(paths, (list, tuple)):
                paths = ["tests"]

            return {
                "paths": [
                    str(path)
                    for path in paths
                ]
            }

        return {}

    @staticmethod
    def _failed(
        context: AgentContext,
        message: str,
    ) -> AgentResult:
        return AgentResult(
            status=AgentResultStatus.FAILED,
            agent_id=context.agent_id,
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=context.started_at,
            finished_at=context.started_at,
            errors=[message],
        )


__all__ = [
    "DeveloperAgent",
]