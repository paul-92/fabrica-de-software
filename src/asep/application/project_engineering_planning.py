"""Bounded, deterministic planning for project engineering executions."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from asep.application.session_context import SessionRuntimeContext
from asep.application.session_memory import SessionMemoryContext
from asep.project_analysis import ProjectAnalysis, ProjectAnalyzer
from asep.projects import (
    ProjectExecution,
    ProjectOperationalPlan,
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanSource,
    ProjectOperationalPlanStep,
)

_ALLOWED_VALIDATION_HINTS = frozenset({
    "compileall", "typecheck", "pytest", "vitest", "eslint", "next_build",
})


class BoundedProjectAnalysis(BaseModel):
    """Safe Application projection of facts needed by engineering planning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    languages: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    package_managers: tuple[str, ...] = ()
    package_manifests: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()
    entrypoints: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    architecture: tuple[str, ...] = ()
    has_tests: bool = False
    file_count: int = Field(default=0, ge=0)
    test_file_count: int = Field(default=0, ge=0)

    @classmethod
    def from_domain(cls, analysis: ProjectAnalysis) -> BoundedProjectAnalysis:
        return cls(
            languages=tuple(item.name for item in analysis.languages),
            frameworks=tuple(item.name for item in analysis.frameworks),
            package_managers=tuple(item.name for item in analysis.package_managers),
            package_manifests=tuple(
                item.manifest.as_posix() for item in analysis.package_managers
            ),
            modules=tuple(item.path.as_posix() for item in analysis.modules),
            entrypoints=tuple(item.path.as_posix() for item in analysis.entrypoints),
            dependencies=tuple(item.name for item in analysis.dependencies),
            architecture=tuple(item.name for item in analysis.architecture),
            has_tests=analysis.statistics.test_file_count > 0,
            file_count=analysis.statistics.file_count,
            test_file_count=analysis.statistics.test_file_count,
        )


class EngineeringPlanningContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    instruction: str
    analysis: BoundedProjectAnalysis
    session_context: SessionRuntimeContext
    memory_context: SessionMemoryContext


class EngineeringDecomposition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    steps: tuple[ProjectOperationalPlanStep, ...] = Field(
        min_length=1, max_length=7
    )
    source: ProjectOperationalPlanSource


class EngineeringTaskDecomposer(Protocol):
    def decompose(
        self, context: EngineeringPlanningContext
    ) -> EngineeringDecomposition: ...


class DeterministicEngineeringTaskDecomposer:
    """Reference decomposition; it makes no semantic file-discovery claims."""
    ai_backed = False

    def decompose(
        self, context: EngineeringPlanningContext
    ) -> EngineeringDecomposition:
        analysis = context.analysis
        application_hints = tuple(dict.fromkeys((*analysis.entrypoints, *analysis.modules)))
        test_hints = ("tests",) if analysis.has_tests else ()
        validation = self._validation_hints(analysis)
        steps = (
            ProjectOperationalPlanStep(
                step_id="inspect-application",
                operation=ProjectOperationalPlanOperation.INSPECT,
                description="Inspect detected application structure and framework entrypoints.",
                target_hints=application_hints,
            ),
            ProjectOperationalPlanStep(
                step_id="inspect-conventions",
                operation=ProjectOperationalPlanOperation.INSPECT,
                description="Inspect implementation conventions relevant to the requested change.",
                dependencies=("inspect-application",),
                target_hints=application_hints,
            ),
            ProjectOperationalPlanStep(
                step_id="inspect-tests",
                operation=ProjectOperationalPlanOperation.INSPECT,
                description="Inspect the existing test structure and conventions.",
                dependencies=("inspect-application",),
                target_hints=test_hints,
            ),
            ProjectOperationalPlanStep(
                step_id="implement-change",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description=f"Implement the requested change: {context.instruction}",
                dependencies=("inspect-conventions",),
                target_hints=application_hints,
            ),
            ProjectOperationalPlanStep(
                step_id="update-tests",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description="Create or update tests for the requested behavior.",
                dependencies=("inspect-tests", "implement-change"),
                target_hints=test_hints,
            ),
            ProjectOperationalPlanStep(
                step_id="validate-change",
                operation=ProjectOperationalPlanOperation.VALIDATE,
                description="Run the bounded validations supported by the detected project.",
                dependencies=("update-tests",),
                validation_hints=validation,
            ),
        )
        return EngineeringDecomposition(
            steps=steps,
            source=ProjectOperationalPlanSource.DETERMINISTIC,
        )

    @staticmethod
    def _validation_hints(analysis: BoundedProjectAnalysis) -> tuple[str, ...]:
        languages = set(analysis.languages)
        if "Python" in languages:
            return ("pytest",)
        return ()


class ProjectEngineeringPlanValidator:
    @property
    def allowed_validation_hints(self) -> frozenset[str]:
        return _ALLOWED_VALIDATION_HINTS

    def validate_steps(
        self, steps: tuple[ProjectOperationalPlanStep, ...]
    ) -> None:
        self.validate(ProjectOperationalPlan(
            execution_id="validation-only",
            steps=steps,
            created_at=datetime.now(UTC),
        ))

    def validate(self, plan: ProjectOperationalPlan) -> None:
        steps = {step.step_id: step for step in plan.steps}
        if len(steps) != len(plan.steps):
            raise ValueError("operational plan step IDs must be unique")
        for step in plan.steps:
            if step.step_id in step.dependencies:
                raise ValueError("operational plan step cannot depend on itself")
            missing = set(step.dependencies) - steps.keys()
            if missing:
                raise ValueError("operational plan dependency does not exist")
            for hint in step.target_hints:
                self._validate_target_hint(hint)
            if not set(step.validation_hints) <= _ALLOWED_VALIDATION_HINTS:
                raise ValueError("unsupported operational validation hint")
        self._validate_acyclic(steps)

    @staticmethod
    def _validate_target_hint(value: str) -> None:
        normalized = value.replace("\\", "/")
        path = PurePosixPath(normalized)
        if (
            path.is_absolute()
            or not normalized
            or ".." in path.parts
            or (path.parts and ":" in path.parts[0])
        ):
            raise ValueError("operational target hint must be a safe relative path")
        if len(path.parts) > 64:
            raise ValueError("operational target hint is too deep")

    @staticmethod
    def _validate_acyclic(steps: dict[str, ProjectOperationalPlanStep]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visiting:
                raise ValueError("operational plan dependencies must be acyclic")
            if step_id in visited:
                return
            visiting.add(step_id)
            for dependency in steps[step_id].dependencies:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in steps:
            visit(step_id)


class ProjectEngineeringPlanningService:
    def __init__(
        self,
        analyzer: ProjectAnalyzer,
        decomposer: EngineeringTaskDecomposer,
        validator: ProjectEngineeringPlanValidator | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._decomposer = decomposer
        self._validator = validator or ProjectEngineeringPlanValidator()

    @property
    def ai_backed(self) -> bool:
        return bool(getattr(self._decomposer, "ai_backed", False))

    def plan(
        self,
        execution: ProjectExecution,
        workspace: Path,
        session_context: SessionRuntimeContext,
        memory_context: SessionMemoryContext,
    ) -> ProjectOperationalPlan:
        analysis = self.analyze(workspace)
        return self.plan_from_analysis(
            execution, analysis, session_context, memory_context
        )

    def analyze(self, workspace: Path) -> BoundedProjectAnalysis:
        return BoundedProjectAnalysis.from_domain(self._analyzer.analyze(workspace))

    def plan_from_analysis(
        self,
        execution: ProjectExecution,
        analysis: BoundedProjectAnalysis,
        session_context: SessionRuntimeContext,
        memory_context: SessionMemoryContext,
    ) -> ProjectOperationalPlan:
        context = EngineeringPlanningContext(
            execution_id=execution.execution_id,
            instruction=execution.instruction,
            analysis=analysis,
            session_context=session_context,
            memory_context=memory_context,
        )
        decomposition = self._decomposer.decompose(context)
        steps = tuple(
            step.model_copy(deep=True)
            for step in decomposition.steps
        )
        plan = ProjectOperationalPlan(
            execution_id=execution.execution_id,
            steps=steps,
            created_at=execution.created_at,
            source=decomposition.source,
        )
        self._validator.validate(plan)
        return plan.model_copy(deep=True)


__all__ = [
    "BoundedProjectAnalysis",
    "DeterministicEngineeringTaskDecomposer",
    "EngineeringDecomposition",
    "EngineeringPlanningContext",
    "EngineeringTaskDecomposer",
    "ProjectEngineeringPlanningService",
    "ProjectEngineeringPlanValidator",
]
