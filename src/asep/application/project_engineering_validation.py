"""Bounded, allowlisted validation for project engineering executions."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
from typing import Protocol

from asep.memory import MemoryFilter
from asep.application.project_engineering_planning import BoundedProjectAnalysis
from asep.projects import (
    ProjectOperationalPlan,
    ProjectValidationFailureAnalysis,
    ProjectValidationFailureCategory,
    ProjectValidationResult,
    ProjectValidationStatus,
    ProjectValidationStrategy,
    ProjectValidationTarget,
)
from asep.tools import ToolCapability, ToolExecutionStatus, ToolExecutor, ToolId, ToolRequest

_MAX_PUBLIC_OUTPUT_CHARS = 20_000
_ORDER = (
    "workspace_changes", "compileall", "typecheck", "pytest", "vitest",
    "eslint", "next_build",
)
_NODE_VALIDATORS = frozenset({"typecheck", "vitest", "eslint", "next_build"})
_PYTHON_VALIDATORS = frozenset({"compileall", "pytest"})
_PYTHON_SUFFIXES = frozenset({".py", ".pyi"})
_FRONTEND_SUFFIXES = frozenset({".js", ".jsx", ".ts", ".tsx", ".css"})
_FRONTEND_CONFIG_NAMES = frozenset({
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "tsconfig.json", "eslint.config.js", "eslint.config.mjs",
    "vitest.config.js", "vitest.config.ts", "next.config.js", "next.config.mjs",
})


class ProjectValidator(Protocol):
    @property
    def validator_id(self) -> str: ...

    def validate(
        self, execution_id: str, workspace: Path, *, sequence: int,
        targets: tuple[str, ...] = (),
    ) -> ProjectValidationResult: ...


class ProjectValidationCapability(Protocol):
    def strategy(
        self, execution_id: str, workspace: Path, plan: ProjectOperationalPlan,
        *, analysis: BoundedProjectAnalysis | None = None,
        changed_paths: tuple[str, ...] = (),
    ) -> ProjectValidationStrategy: ...

    def validate_strategy(
        self, strategy: ProjectValidationStrategy, workspace: Path, *,
        start_sequence: int, validators: tuple[str, ...] | None = None,
    ) -> tuple[ProjectValidationResult, ...]: ...

    def analyze_failure(
        self, result: ProjectValidationResult,
    ) -> ProjectValidationFailureAnalysis: ...


class _ToolProjectValidator:
    def __init__(
        self, validator_id: str, tool_id: str, capability: str,
        payload_key: str, tools: ToolExecutor, *, multiple_targets: bool = True,
    ) -> None:
        self._validator_id = validator_id
        self._tool_id = tool_id
        self._capability = capability
        self._payload_key = payload_key
        self._tools = tools
        self._multiple_targets = multiple_targets
        self._filter = MemoryFilter()

    @property
    def validator_id(self) -> str:
        return self._validator_id

    def validate(
        self, execution_id: str, workspace: Path, *, sequence: int,
        targets: tuple[str, ...] = (),
    ) -> ProjectValidationResult:
        result = self._tools.execute(ToolRequest(
            execution_id=f"{execution_id}-validation-{sequence}",
            tool_id=ToolId(value=self._tool_id),
            capability=ToolCapability(id=self._capability),
            workspace=workspace,
            payload={
                self._payload_key: (
                    list(targets or (".",))
                    if self._multiple_targets
                    else (targets or (".",))[0]
                )
            },
            metadata={"project_execution_id": execution_id},
            workflow_execution_id=execution_id,
        ))
        output = result.output if isinstance(result.output, Mapping) else {}
        exit_code = output.get("exit_code", -1)
        command = output.get("command", ())
        passed = result.status is ToolExecutionStatus.SUCCEEDED and exit_code == 0
        safe_output = self._safe_output(output)
        unavailable = self._validator_unavailable(safe_output)
        return ProjectValidationResult(
            execution_id=execution_id,
            sequence=sequence,
            validator=self.validator_id,
            command=tuple(str(item) for item in command) or (self.validator_id,),
            exit_code=exit_code if isinstance(exit_code, int) else -1,
            status=(
                ProjectValidationStatus.PASSED if passed
                else ProjectValidationStatus.SKIPPED if unavailable
                else ProjectValidationStatus.FAILED
            ),
            output=safe_output,
            completed_at=result.completed_at,
        )

    def _safe_output(self, output: Mapping[str, object]) -> str:
        combined = "\n".join(
            value.strip() for key in ("stdout", "stderr")
            if isinstance((value := output.get(key)), str) and value.strip()
        )
        safe, _, _ = self._filter.sanitize(combined, {})
        return safe if len(safe) <= _MAX_PUBLIC_OUTPUT_CHARS else safe[:_MAX_PUBLIC_OUTPUT_CHARS] + "\n[output truncated]"

    def _validator_unavailable(self, output: str) -> bool:
        lowered = output.casefold()
        module = "pytest" if self.validator_id == "pytest" else self.validator_id
        return any(marker in lowered for marker in (
            f"no module named {module}",
            f"no module named '{module}'",
            "command not found",
            "is not recognized as an internal or external command",
        ))


class _WorkspaceChangeEvidenceValidator:
    validator_id = "workspace_changes"

    def validate(
        self, execution_id: str, workspace: Path, *, sequence: int,
        targets: tuple[str, ...] = (),
    ) -> ProjectValidationResult:
        root = workspace.resolve()
        present = bool(targets) and all(
            ProjectValidationService._confined_path(
                root, PurePosixPath(target.replace("\\", "/")),
            ).exists()
            for target in targets
        )
        return ProjectValidationResult(
            execution_id=execution_id,
            sequence=sequence,
            validator=self.validator_id,
            command=("internal", "workspace-change-evidence"),
            exit_code=0 if present else 1,
            status=(
                ProjectValidationStatus.PASSED
                if present else ProjectValidationStatus.FAILED
            ),
            output=(
                f"Verified {len(targets)} changed workspace artifact(s)."
                if present else "Changed workspace artifact evidence is missing."
            ),
            completed_at=datetime.now(UTC),
        )


class ProjectValidationService:
    def __init__(self, tools: ToolExecutor) -> None:
        validators = (
            _WorkspaceChangeEvidenceValidator(),
            _ToolProjectValidator("compileall", "compileall", "compile", "targets", tools),
            _ToolProjectValidator(
                "typecheck", "typecheck", "typecheck", "package_root", tools,
                multiple_targets=False,
            ),
            _ToolProjectValidator("pytest", "run-tests", "test", "paths", tools),
            _ToolProjectValidator(
                "vitest", "vitest", "frontend_test", "package_root", tools,
                multiple_targets=False,
            ),
            _ToolProjectValidator(
                "eslint", "eslint", "lint", "package_root", tools,
                multiple_targets=False,
            ),
            _ToolProjectValidator(
                "next_build", "next-build", "build", "package_root", tools,
                multiple_targets=False,
            ),
        )
        self._validators = {item.validator_id: item for item in validators}

    def validate(
        self, execution_id: str, workspace: Path, *, sequence: int,
        test_paths: tuple[str, ...] | None = None,
    ) -> ProjectValidationResult:
        return self._validators["pytest"].validate(
            execution_id, workspace, sequence=sequence,
            targets=test_paths or (("tests",) if (workspace / "tests").is_dir() else (".",)),
        )

    def validate_plan(
        self, execution_id: str, workspace: Path, plan: ProjectOperationalPlan,
        *, start_sequence: int,
    ) -> tuple[ProjectValidationResult, ...]:
        strategy = self.strategy(execution_id, workspace, plan)
        return self.validate_strategy(strategy, workspace, start_sequence=start_sequence)

    def strategy(
        self, execution_id: str, workspace: Path, plan: ProjectOperationalPlan,
        *, analysis: BoundedProjectAnalysis | None = None,
        changed_paths: tuple[str, ...] = (),
    ) -> ProjectValidationStrategy:
        hints = {hint for step in plan.steps for hint in step.validation_hints}
        unsupported = hints - self._validators.keys()
        if unsupported:
            raise ValueError("project validation hint is not executable")
        selected = self._selected_validators(
            workspace, hints, analysis, changed_paths,
        )
        ordered = tuple(item for item in _ORDER if item in selected)
        targets = tuple(
            ProjectValidationTarget(
                validator_id=item,
                targets=self._safe_targets(
                    workspace, item, changed_paths, analysis=analysis,
                ),
            )
            for item in ordered
        )
        return ProjectValidationStrategy(
            execution_id=execution_id,
            validators=ordered,
            reason=(
                "Allowlisted validators selected from the operational plan; "
                f"languages={analysis.languages if analysis is not None else ()}; "
                f"has_tests={analysis.has_tests if analysis is not None else (workspace / 'tests').is_dir()}; "
                f"changed_paths={len(changed_paths)}."
            ),
            target_hints=targets,
        )

    def validate_strategy(
        self, strategy: ProjectValidationStrategy, workspace: Path, *,
        start_sequence: int, validators: tuple[str, ...] | None = None,
    ) -> tuple[ProjectValidationResult, ...]:
        selected = validators or strategy.validators
        if any(item not in strategy.validators for item in selected):
            raise ValueError("validator is not required by this strategy")
        target_map = {item.validator_id: item.targets for item in strategy.target_hints}
        results: list[ProjectValidationResult] = []
        for validator_id in selected:
            validator = self._validators.get(validator_id)
            if validator is None:
                raise ValueError("project validator is not registered")
            result = validator.validate(
                strategy.execution_id, workspace,
                sequence=start_sequence + len(results),
                targets=target_map.get(validator_id, ()),
            )
            results.append(result)
            if result.status is ProjectValidationStatus.FAILED:
                break
        return tuple(results)

    def analyze_failure(self, result: ProjectValidationResult) -> ProjectValidationFailureAnalysis:
        lowered = result.output.lower()
        if result.validator in {"compileall", "typecheck"} or "syntaxerror" in lowered:
            category = ProjectValidationFailureCategory.SYNTAX_OR_COMPILE_ERROR
        elif "importerror" in lowered or "modulenotfounderror" in lowered:
            category = ProjectValidationFailureCategory.IMPORT_ERROR
        elif "assert" in lowered:
            category = ProjectValidationFailureCategory.ASSERTION_FAILURE
        elif result.validator in {"pytest", "vitest"}:
            category = ProjectValidationFailureCategory.TEST_FAILURE
        elif result.validator == "eslint":
            category = ProjectValidationFailureCategory.LINT_FAILURE
        elif result.validator == "next_build":
            category = (
                ProjectValidationFailureCategory.SYNTAX_OR_COMPILE_ERROR
                if any(marker in lowered for marker in (
                    "syntaxerror", "type error", "typescript error", "failed to compile",
                ))
                else ProjectValidationFailureCategory.BUILD_FAILURE
            )
        else:
            category = ProjectValidationFailureCategory.UNKNOWN
        return ProjectValidationFailureAnalysis(
            execution_id=result.execution_id,
            validator_id=result.validator,
            category=category,
            summary=f"{result.validator} validation failed with exit code {result.exit_code}.",
            evidence=result.output,
        )

    @staticmethod
    def _selected_validators(
        workspace: Path, hints: set[str], analysis: BoundedProjectAnalysis | None,
        changed_paths: tuple[str, ...],
    ) -> set[str]:
        if not changed_paths:
            return hints or {"workspace_changes"}

        python_changed = any(
            PurePosixPath(path.replace("\\", "/")).suffix.lower()
            in _PYTHON_SUFFIXES
            for path in changed_paths
        )
        frontend_changed = any(
            (
                (normalized := PurePosixPath(path.replace("\\", "/"))).suffix.lower()
                in _FRONTEND_SUFFIXES
                or normalized.name.lower() in _FRONTEND_CONFIG_NAMES
                or normalized.name.lower().startswith("tsconfig.")
            )
            for path in changed_paths
        )
        languages = set(analysis.languages if analysis is not None else ())
        has_python = "Python" in languages or python_changed
        has_frontend = bool(languages & {"JavaScript", "TypeScript"}) or frontend_changed
        node_applicable = (
            ProjectValidationService._node_validators(
                workspace, changed_paths, analysis,
            ) if has_frontend else set()
        )
        pytest_applicable = (
            ProjectValidationService._pytest_configured(workspace, analysis)
            and (
                (analysis is not None and analysis.has_tests)
                or any(
                    "tests" in PurePosixPath(path.replace("\\", "/")).parts
                    or PurePosixPath(path.replace("\\", "/")).name.startswith("test_")
                    for path in changed_paths
                )
            )
        )

        selected: set[str] = set()
        if python_changed and has_python:
            selected.add("compileall")
            if pytest_applicable:
                selected.add("pytest")
        if frontend_changed and has_frontend:
            selected.update(node_applicable)
        if not selected:
            selected.add("workspace_changes")
        else:
            if has_python and pytest_applicable:
                selected.update(hints & {"pytest"})
            if has_frontend:
                selected.update(hints & node_applicable)
        return selected

    @staticmethod
    def _pytest_configured(
        workspace: Path, analysis: BoundedProjectAnalysis | None,
    ) -> bool:
        dependencies = {
            item.casefold() for item in analysis.dependencies
        } if analysis is not None else set()
        return "pytest" in dependencies or any(
            (workspace / name).is_file()
            for name in ("pytest.ini", "tox.ini", "conftest.py")
        )

    @staticmethod
    def _node_validators(
        workspace: Path, changed_paths: tuple[str, ...],
        analysis: BoundedProjectAnalysis | None,
    ) -> set[str]:
        try:
            package_root = ProjectValidationService._safe_package_root(
                workspace, changed_paths, analysis,
            )
        except ValueError:
            raise
        root = workspace if package_root == "." else workspace / package_root
        try:
            package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            package = {}
        scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        dependencies = {
            str(item).casefold()
            for section in ("dependencies", "devDependencies")
            if isinstance(package, dict)
            and isinstance((values := package.get(section)), dict)
            for item in values
        }
        selected: set[str] = set()
        if "typecheck" in scripts or (root / "tsconfig.json").is_file():
            selected.add("typecheck")
        if (
            "test" in scripts or "vitest" in dependencies
            or any((root / name).is_file() for name in ("vitest.config.js", "vitest.config.ts"))
        ):
            selected.add("vitest")
        if (
            "lint" in scripts or "eslint" in dependencies
            or any((root / name).is_file() for name in ("eslint.config.js", "eslint.config.mjs"))
        ):
            selected.add("eslint")
        if "build" in scripts and (
            "next" in dependencies
            or any((root / name).is_file() for name in ("next.config.js", "next.config.mjs"))
        ):
            selected.add("next_build")
        return selected

    @staticmethod
    def _safe_targets(
        workspace: Path, validator_id: str, changed_paths: tuple[str, ...],
        *, analysis: BoundedProjectAnalysis | None = None,
    ) -> tuple[str, ...]:
        candidates = tuple(dict.fromkeys(
            path for path in changed_paths
            if validator_id != "compileall" or path.endswith(".py")
        ))
        if validator_id == "workspace_changes":
            return candidates
        if validator_id in _NODE_VALIDATORS:
            return (
                ProjectValidationService._safe_package_root(
                    workspace, changed_paths, analysis,
                ),
            )
        selected: list[str] = []
        root = workspace.resolve()
        for raw in candidates:
            normalized = raw.replace("\\", "/")
            path = PurePosixPath(normalized)
            if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
                raise ValueError("validation target must be a safe relative path")
            resolved = (root / Path(*path.parts)).resolve()
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise ValueError("validation target escapes workspace") from exc
            if resolved.exists():
                selected.append(path.as_posix())
        if validator_id == "pytest":
            return ("tests",) if (root / "tests").is_dir() else (".",)
        return tuple(selected) or (".",)

    @staticmethod
    def _safe_package_root(
        workspace: Path, changed_paths: tuple[str, ...],
        analysis: BoundedProjectAnalysis | None,
    ) -> str:
        root = workspace.resolve()
        candidates: set[Path] = set()
        if (root / "package.json").is_file():
            candidates.add(root)
        if analysis is not None:
            for manifest in analysis.package_manifests:
                normalized = PurePosixPath(manifest.replace("\\", "/"))
                if normalized.name.lower() != "package.json":
                    continue
                ProjectValidationService._confined_path(root, normalized)
                candidate = (root / Path(*normalized.parts)).resolve().parent
                if (candidate / "package.json").is_file():
                    candidates.add(candidate)
        frontend_paths: list[Path] = []
        for raw in changed_paths:
            normalized = PurePosixPath(raw.replace("\\", "/"))
            resolved = ProjectValidationService._confined_path(root, normalized)
            frontend_paths.append(resolved)
            current = resolved if resolved.is_dir() else resolved.parent
            while current == root or root in current.parents:
                if (current / "package.json").is_file():
                    candidates.add(current)
                    break
                if current == root:
                    break
                current = current.parent
        relevant = {
            candidate for candidate in candidates
            if not frontend_paths or any(
                path == candidate or candidate in path.parents
                for path in frontend_paths
            )
        }
        if len(relevant) != 1:
            raise ValueError("frontend validation requires one safe package root")
        selected = next(iter(relevant))
        relative = selected.relative_to(root).as_posix()
        return relative or "."

    @staticmethod
    def _confined_path(root: Path, path: PurePosixPath) -> Path:
        if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
            raise ValueError("validation target must be a safe relative path")
        resolved = (root / Path(*path.parts)).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError("validation target escapes workspace") from exc
        return resolved


__all__ = ["ProjectValidationCapability", "ProjectValidationService", "ProjectValidator"]
