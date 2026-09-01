from __future__ import annotations

import json
from typing import Mapping, Any

from pydantic import BaseModel, ConfigDict, ValidationError

from asep.ai_runtime.contracts import AIRuntime
from asep.ai_runtime.models import AIRuntimeExecutionMode, AIRuntimeRequest
from asep.application.project_engineering_agent_execution import (
    AIImplementationResult,
    EngineeringFileChange,
    EngineeringImplementationContext,
)
from asep.projects import (
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanStep,
)


class EngineeringImplementationError(ValueError):
    """AI Runtime output did not satisfy the engineering implementation contract."""


class _ProviderImplementation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    changes: tuple[EngineeringFileChange, ...]


class AIRuntimeEngineeringImplementationProvider:
    """Produces bounded file changes through a provider-agnostic AIRuntime."""

    ai_backed = True
    metered_by_runtime = False

    def __init__(self, runtime: AIRuntime) -> None:
        self._runtime = runtime

    @property
    def identity(self):
        return self._runtime.identity

    def supports(self, step: ProjectOperationalPlanStep) -> bool:
        return step.operation is ProjectOperationalPlanOperation.IMPLEMENT

    def invoke_ai(
        self,
        context: EngineeringImplementationContext,
    ) -> AIImplementationResult:
        result = self._runtime.execute(
            AIRuntimeRequest(
                instruction=self._instruction(context),
                context={},
                workspace=context.workspace,
                metadata={
                    "purpose": "project_engineering_implementation",
                    "execution_id": context.execution_id,
                    "project_id": context.project_id,
                    "session_id": context.session_id,
                    "step_id": context.step.step_id,
                },
                execution_mode=AIRuntimeExecutionMode.READ_ONLY,
            )
        )

        try:
            raw = json.loads(result.output)
            provider_result = _ProviderImplementation.model_validate(raw)
        except (
            json.JSONDecodeError,
            ValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise EngineeringImplementationError(
                "AI implementation output is invalid"
            ) from exc

        return AIImplementationResult(
            changes=provider_result.changes,
            identity=result.identity,
            provider=result.identity.runtime_id,
            usage=result.usage,
            provider_request_id=self._provider_request_id(result.metadata),
            already_metered=False,
        )

    @staticmethod
    def _provider_request_id(
        metadata: Mapping[str, Any],
    ) -> str | None:
        value = metadata.get("provider_request_id")

        if isinstance(value, str) and value.strip():
            return value

        return None

    @staticmethod
    def _instruction(
        context: EngineeringImplementationContext,
    ) -> str:
        bounded = {
            "task": context.task,
            "project_analysis": context.analysis.model_dump(mode="json"),
            "plan": context.plan.model_dump(mode="json"),
            "step": context.step.model_dump(mode="json"),
            "approved_dependency_plan": context.dependency_plan,
            "dependency_results": [
                result.model_dump(mode="json")
                for result in context.dependency_results
            ],
            "contract": {
                "root_fields": ["changes"],
                "change_fields": [
                    "relative_path",
                    "content",
                    "operation",
                ],
                "operations": [
                    "create_or_replace",
                ],
            },
        }

        return (
            "Return exactly one JSON object matching the supplied contract. "
            "Do not modify the workspace. "
            "Do not run commands. "
            "Return only the proposed file changes required for the current "
            "implementation step. "
            "When approved_dependency_plan is present, treat it as authoritative. "
            "Use only dependency versions explicitly approved there and do not "
            "invent, upgrade, downgrade, or substitute dependency versions. "
            "If the requested implementation requires those dependencies, "
            "materialize the required manifests and configuration using the "
            "approved versions. "
            "Paths must be safe relative workspace paths. "
            "Do not include markdown fences or explanatory prose.\n"
            + json.dumps(
                bounded,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )


__all__ = [
    "AIRuntimeEngineeringImplementationProvider",
    "EngineeringImplementationError",
]
