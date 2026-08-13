import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asep.ai_runtime import AIRuntimeExecutionMode, AIRuntimeIdentity, InMemoryAIRuntimeRegistry
from asep.api import create_project_engineering_operational_composition
from asep.application import (
    EngineeringDecomposition,
    EngineeringFileChange,
    ProjectAIRuntimeExecutionRequest,
)
from asep.configuration import ApplicationSettings
from asep.projects import (
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanSource,
    ProjectOperationalPlanStep,
)


class NeverRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="unused")

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("external AI runtime must not execute supported steps")


class PaginationDecomposer:
    def decompose(self, context):
        steps = (
            ProjectOperationalPlanStep(
                step_id="backend",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description="Paginate the product repository.",
                target_hints=("products.py",),
            ),
            ProjectOperationalPlanStep(
                step_id="api",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description="Expose pagination through FastAPI.",
                dependencies=("backend",),
                target_hints=("api.py",),
            ),
            ProjectOperationalPlanStep(
                step_id="frontend",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description="Add pagination to the Next.js product page.",
                dependencies=("api",),
                target_hints=("web/app/products/page.tsx",),
            ),
            ProjectOperationalPlanStep(
                step_id="tests",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description="Cover backend and frontend pagination.",
                dependencies=("frontend",),
                target_hints=("tests", "web/app/products/page.test.ts"),
            ),
            ProjectOperationalPlanStep(
                step_id="validate",
                operation=ProjectOperationalPlanOperation.VALIDATE,
                description="Run the bounded full-stack validators.",
                dependencies=("tests",),
                validation_hints=(
                    "compileall", "typecheck", "pytest", "vitest", "eslint", "next_build",
                ),
            ),
        )
        return EngineeringDecomposition(
            steps=steps, source=ProjectOperationalPlanSource.AI,
        )


class PaginationProvider:
    def supports(self, step):
        return True

    def changes_for(self, context):
        changes = {
            "backend": (
                EngineeringFileChange(
                    relative_path="products.py",
                    content=(
                        "PRODUCTS = [{'id': index, 'name': f'Product {index}'} "
                        "for index in range(1, 8)]\n\n"
                        "def list_products(offset: int = 0, limit: int = 3):\n"
                        "    return PRODUCTS[offset:offset + limit]\n"
                    ),
                ),
            ),
            "api": (
                EngineeringFileChange(
                    relative_path="api.py",
                    content=(
                        "from fastapi import FastAPI, Query\n"
                        "from products import list_products\n\n"
                        "app = FastAPI()\n\n"
                        "@app.get('/products')\n"
                        "def products(offset: int = Query(0, ge=0), "
                        "limit: int = Query(3, ge=1, le=50)):\n"
                        "    return {'items': list_products(offset, limit), "
                        "'offset': offset, 'limit': limit}\n"
                    ),
                ),
            ),
            "frontend": (
                EngineeringFileChange(
                    relative_path="web/app/products/page.tsx",
                    content=(
                        "'use client';\n"
                        "import { useState } from 'react';\n\n"
                        "export default function ProductsPage() {\n"
                        "  const [offset, setOffset] = useState(0);\n"
                        "  const limit = 3;\n"
                        "  const endpoint = `/products?offset=${offset}&limit=${limit}`;\n"
                        "  return <main><h1>Products</h1><output>{endpoint}</output>"
                        "<button onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</button>"
                        "<button onClick={() => setOffset(offset + limit)}>Next</button></main>;\n"
                        "}\n"
                    ),
                ),
            ),
            "tests": (
                EngineeringFileChange(
                    relative_path="tests/test_products.py",
                    content=(
                        "from fastapi.testclient import TestClient\n"
                        "from api import app\n\n"
                        "def test_products_are_paginated_through_the_api():\n"
                        "    response = TestClient(app).get('/products?offset=3&limit=2')\n"
                        "    assert response.status_code == 200\n"
                        "    assert [item['id'] for item in response.json()['items']] == [4, 5]\n"
                    ),
                ),
                EngineeringFileChange(
                    relative_path="web/app/products/page.test.ts",
                    content=(
                        "import { describe, expect, it } from 'vitest';\n"
                        "import fs from 'node:fs';\n\n"
                        "const source = fs.readFileSync('app/products/page.tsx', 'utf8');\n"
                        "describe('product pagination', () => {\n"
                        "  it('passes offset and limit and renders controls', () => {\n"
                        "    expect(source).toMatch(/offset=\\$\\{offset\\}&limit=\\$\\{limit\\}/);\n"
                        "    expect(source).toMatch(/>Previous<.*>Next</s);\n"
                        "  });\n"
                        "});\n"
                    ),
                ),
            ),
        }
        return changes[context.step.step_id]


def write_file(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_fullstack_fixture(root: Path) -> None:
    write_file(
        root, "products.py",
        "PRODUCTS = [{'id': 1, 'name': 'Product 1'}]\n\n"
        "def list_products():\n    return PRODUCTS\n",
    )
    write_file(
        root, "api.py",
        "from fastapi import FastAPI\nfrom products import list_products\n\n"
        "app = FastAPI()\n\n@app.get('/products')\n"
        "def products():\n    return {'items': list_products()}\n",
    )
    write_file(
        root, "tests/test_products.py",
        "from products import list_products\n\n"
        "def test_products_list_starts_green():\n"
        "    assert list_products()[0]['id'] == 1\n",
    )
    write_file(
        root, "web/app/products/page.tsx",
        "import React from 'react';\nexport default function ProductsPage() {\n"
        "  return <main><h1>Products</h1></main>;\n}\n",
    )
    write_file(
        root, "web/app/products/page.test.ts",
        "import { describe, expect, it } from 'vitest';\nimport fs from 'node:fs';\n\n"
        "const source = fs.readFileSync('app/products/page.tsx', 'utf8');\n"
        "describe('products page baseline', () => {\n"
        "  it('renders products', () => expect(source).toMatch(/Products/));\n"
        "});\n",
    )
    scripts = {
        "typecheck": "tsc --noEmit",
        "test": "vitest run",
        "lint": "eslint .",
        "build": "next build --webpack",
    }
    write_file(
        root, "web/package.json",
        json.dumps({
            "name": "pagination-fixture", "private": True, "scripts": scripts,
            "dependencies": {"next": "16.3.0", "react": "19.2.8", "react-dom": "19.2.8"},
            "devDependencies": {
                "@types/node": "^22.10.0", "@types/react": "^19.0.0",
                "@types/react-dom": "^19.0.0", "typescript": "^5.7.0",
                "vitest": "^4.1.10", "eslint": "^9.0.0", "eslint-config-next": "16.3.0",
            },
        }),
    )
    write_file(
        root, "web/tsconfig.json",
        json.dumps({
            "compilerOptions": {
                "target": "ES2020", "lib": ["dom", "esnext"], "strict": True,
                "noEmit": True, "module": "esnext", "moduleResolution": "bundler",
                "jsx": "react-jsx", "esModuleInterop": True,
            },
            "include": ["app/**/*.ts", "app/**/*.tsx"],
        }),
    )
    write_file(
        root, "web/eslint.config.mjs",
        "import { defineConfig, globalIgnores } from 'eslint/config';\n"
        "import nextVitals from 'eslint-config-next/core-web-vitals';\n"
        "export default defineConfig([...nextVitals, globalIgnores(['.next/**'])]);\n",
    )
    write_file(
        root, "web/app/layout.tsx",
        "import type { ReactNode } from 'react';\n"
        "export default function Layout({ children }: { children: ReactNode }) {\n"
        "  return <html><body>{children}</body></html>;\n}\n",
    )


def run_baseline(root: Path, npm: str) -> None:
    commands = (
        (sys.executable, "-m", "compileall", "-q", "."),
        (sys.executable, "-m", "pytest", "-q", "tests"),
    )
    for command in commands:
        subprocess.run(command, cwd=root, check=True, shell=False, capture_output=True)
    for script in ("typecheck", "test", "lint", "build"):
        subprocess.run(
            (npm, "run", script), cwd=root / "web", check=True,
            shell=False, capture_output=True,
        )


def link_preinstalled_node_modules(link: Path, target: Path) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ("cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)),
            check=True,
            shell=False,
            capture_output=True,
            text=True,
        )
        return
    link.symlink_to(target, target_is_directory=True)


def test_dependency_reuse_link_is_unprivileged_and_disposable(tmp_path: Path) -> None:
    installed = tmp_path / "installed" / "node_modules"
    installed.mkdir(parents=True)
    marker = installed / "dependency.txt"
    marker.write_text("available", encoding="utf-8")
    link = tmp_path / "fixture" / "node_modules"
    link.parent.mkdir()

    link_preinstalled_node_modules(link, installed)

    assert (link / "dependency.txt").read_text(encoding="utf-8") == "available"
    assert link.samefile(installed)


def test_fullstack_pagination_acceptance_uses_one_execution(tmp_path: Path) -> None:
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if npm is None:
        pytest.skip("real npm runtime is required for the full-stack acceptance")
    installed_modules = Path(__file__).parents[3] / "frontend" / "node_modules"
    if not installed_modules.is_dir():
        pytest.skip("preinstalled frontend dependencies are required for acceptance")
    runtime = NeverRuntime()
    registry = InMemoryAIRuntimeRegistry()
    registry.register(runtime)
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(hosted_root=tmp_path / "hosted"), runtime_registry=registry,
        engineering_decomposer=PaginationDecomposer(),
        implementation_provider=PaginationProvider(),
    )
    client = TestClient(composition.app)
    project = client.post("/api/v1/projects", json={"name": "Full Stack Pagination"}).json()
    workspace = tmp_path / "hosted" / "legacy-local" / project["project_id"] / "workspace"
    write_fullstack_fixture(workspace)
    link_preinstalled_node_modules(workspace / "web" / "node_modules", installed_modules)
    run_baseline(workspace, npm)
    artifact = workspace / "web" / ".next"
    quarantined_artifact = workspace.parent / ".baseline-next"
    artifact.rename(quarantined_artifact)
    shutil.rmtree(quarantined_artifact, ignore_errors=True)
    session = client.post(
        f"/api/v1/projects/{project['project_id']}/sessions",
        json={"title": "Product pagination"},
    ).json()

    result = composition.project_engineering_execution.execute(
        ProjectAIRuntimeExecutionRequest(
            project_id=project["project_id"], session_id=session["session_id"],
            runtime_id="codex",
            instruction="Add pagination to the product list across backend, API, frontend and tests.",
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        )
    )

    execution = result.execution
    expected = ["compileall", "typecheck", "pytest", "vitest", "eslint", "next_build"]
    assert runtime.calls == 0
    assert execution.status.value == "succeeded"
    assert execution.validation_strategy.validators == tuple(expected)
    assert [item.validator for item in execution.validations] == expected
    assert all(item.status.value == "passed" for item in execution.validations)
    assert all(item.execution_id == execution.execution_id for item in execution.validations)
    assert all(item.execution_id == execution.execution_id for item in execution.step_results)
    assert execution.operational_plan.execution_id == execution.execution_id
    assert execution.validation_strategy.execution_id == execution.execution_id
    assert execution.quality_gate.run_id == execution.execution_id
    assert execution.quality_gate.decision.value == "APPROVED"
    assert execution.repair is None
    assert {item.path for item in execution.changes} >= {
        "products.py", "api.py", "tests/test_products.py",
        "web/app/products/page.tsx", "web/app/products/page.test.ts",
    }
    assert [item.command[-2:] for item in execution.validations if item.validator in {
        "typecheck", "vitest", "eslint", "next_build",
    }] == [
        ("run", "typecheck"), ("run", "test"), ("run", "lint"), ("run", "build"),
    ]
    history = client.get(
        f"/api/v1/projects/{project['project_id']}/sessions/{session['session_id']}/executions"
    ).json()["items"]
    assert [item["execution_id"] for item in history] == [execution.execution_id]
