"""AI Runtime adapter for bounded Project Engineering decomposition."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from asep.ai_runtime.contracts import AIRuntime
from asep.ai_runtime.models import AIRuntimeExecutionMode, AIRuntimeRequest
from asep.application.project_engineering_planning import (
    DeterministicEngineeringTaskDecomposer,
    EngineeringDecomposition,
    EngineeringPlanningContext,
    ProjectEngineeringPlanValidator,
)
from asep.projects import ProjectOperationalPlanSource, ProjectOperationalPlanStep


class EngineeringDecompositionError(ValueError):
    """Provider output did not satisfy the bounded decomposition contract."""


class _ProviderDecomposition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    steps: tuple[ProjectOperationalPlanStep, ...] = Field(
        min_length=1, max_length=7
    )


class CodexEngineeringTaskDecomposer:
    """Consumes an AIRuntime without coupling Application to Codex internals."""

    def __init__(
        self,
        runtime: AIRuntime,
        *,
        fallback: DeterministicEngineeringTaskDecomposer | None = None,
        validator: ProjectEngineeringPlanValidator | None = None,
    ) -> None:
        self._runtime = runtime
        self._fallback = fallback
        self._validator = validator or ProjectEngineeringPlanValidator()

    def decompose(self, context: EngineeringPlanningContext) -> EngineeringDecomposition:
        try:
            result = self._runtime.execute(AIRuntimeRequest(
                instruction=self._instruction(context),
                context={},
                metadata={"purpose": "project_engineering_planning"},
                execution_mode=AIRuntimeExecutionMode.READ_ONLY,
            ))
            try:
                raw = json.loads(result.output)
                provider = _ProviderDecomposition.model_validate(raw)
                self._validator.validate_steps(provider.steps)
            except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
                raise EngineeringDecompositionError(
                    "AI planning output is invalid"
                ) from exc
            return EngineeringDecomposition(
                steps=provider.steps,
                source=ProjectOperationalPlanSource.AI,
            )
        except Exception:
            if self._fallback is None:
                raise
            fallback = self._fallback.decompose(context)
            return EngineeringDecomposition(
                steps=fallback.steps,
                source=ProjectOperationalPlanSource.DETERMINISTIC_FALLBACK,
            )

    @staticmethod
    def _instruction(context: EngineeringPlanningContext) -> str:
        bounded = {
            "task": context.instruction,
            "project_analysis": context.analysis.model_dump(mode="json"),
            "recent_context": context.session_context.model_dump(mode="json"),
            "session_memory": context.memory_context.model_dump(mode="json"),
            "contract": {
                "root_fields": ["steps"],
                "step_fields": [
                    "step_id",
                    "operation",
                    "description",
                    "dependencies",
                    "target_hints",
                    "validation_hints",
                ],
                "operations": ["inspect", "implement", "validate"],
                "validation_hints": sorted(
                    ProjectEngineeringPlanValidator().allowed_validation_hints
                ),
                "maximum_steps": 7,
            },
        }
        return (
            "Return exactly one JSON object matching the supplied contract. "
            "Use only bounded facts. Target hints are relative candidate areas, "
            "not claims that files exist. Do not include commands or identifiers "
            "outside the contract.\n"
            + json.dumps(
                bounded,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )


__all__ = ["CodexEngineeringTaskDecomposer", "EngineeringDecompositionError"]
