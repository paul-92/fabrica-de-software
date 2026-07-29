from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest


def write_file(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return path


@pytest.fixture
def sample_repository(tmp_path: Path) -> Path:
    write_file(
        tmp_path,
        "registry/agents.yaml",
        """
        version: 0.1.0
        agents:
          - id: orchestrator
            name: Orchestrator
            version: 0.1.0
            status: active
            contract: ../contracts/orchestrator.yaml
            manual: ../agents/orchestrator.md
            capabilities: [coordination]
            department: Operations
            dependencies: [core-system]
            applicable_project_types: [software]
          - id: business-analyst
            name: Business Analyst
            version: 0.1.0
            status: active
            contract: ../contracts/business-analyst.yaml
            manual: ../agents/business-analyst.md
            capabilities: [analysis]
            department: Business
            dependencies: [core-system]
            applicable_project_types: [software]
        """,
    )
    write_file(
        tmp_path,
        "registry/contracts.yaml",
        """
        version: 0.1.0
        contracts:
          - id: orchestrator
            version: 0.1.0
            path: ../contracts/orchestrator.yaml
          - id: business-analyst
            version: 0.1.0
            path: ../contracts/business-analyst.yaml
        """,
    )
    write_file(
        tmp_path,
        "registry/workflows.yaml",
        """
        version: 0.1.0
        workflows:
          - id: software-project
            name: Software Project
            version: 0.1.0
            purpose: Teste
            project_types: [software]
            stages: [intake]
            agents: [business-analyst]
            conditions: []
            gates: [QG-INTAKE]
            approvals: []
            path: ../workflows/software-project.yaml
        """,
    )
    write_file(
        tmp_path,
        "registry/quality-gates.yaml",
        """
        version: 0.1.0
        quality_gates:
          - id: QG-INTAKE
            owner: orchestrator
            definition: ../core/QUALITY.md
        """,
    )
    write_file(
        tmp_path,
        "registry/playbooks.yaml",
        """
        version: 0.1.0
        playbooks:
          - id: intake
            version: 0.1.0
            path: ../playbooks/intake.md
        """,
    )
    write_file(
        tmp_path,
        "registry/knowledge.yaml",
        """
        version: 0.1.0
        knowledge:
          - id: foundations
            version: 0.1.0
            path: ../knowledge/foundations.md
        """,
    )
    write_file(tmp_path, "agents/orchestrator.md", "# Orchestrator")
    write_file(tmp_path, "agents/business-analyst.md", "# Business Analyst")
    write_file(
        tmp_path,
        "contracts/orchestrator.yaml",
        """
        id: orchestrator
        name: Orchestrator
        version: 0.1.0
        status: active
        department: operations
        role: orchestrator
        reports_to: executive
        mission: Coordenar
        capabilities: [coordination]
        receives: [project-brief]
        required_inputs: [project-brief]
        optional_inputs: []
        produces: [workflow-run]
        required_outputs: [workflow-run]
        consults:
          - ../AGENTS.md
          - ../core/QUALITY.md
          - ../agents/orchestrator.md
        quality_gates: [QG-INTAKE]
        approval_rules: [human-gate]
        next_agents: []
        cannot: [implement]
        human_approval_required: [production]
        escalation_conditions: [missing-input]
        success_criteria: [output-exists]
        failure_conditions: [missing-output]
        """,
    )
    write_file(tmp_path, "AGENTS.md", "# Agents")
    write_file(
        tmp_path,
        "contracts/business-analyst.yaml",
        """
        id: business-analyst
        name: Business Analyst
        version: 0.1.0
        status: active
        department: business
        role: business-analysis
        reports_to: orchestrator
        mission: Analisar
        capabilities: [analysis]
        receives: [project-brief]
        required_inputs: [project-brief]
        optional_inputs: []
        produces: [execution-summary]
        required_outputs: [execution-summary]
        consults:
          - ../AGENTS.md
          - ../core/QUALITY.md
          - ../agents/business-analyst.md
        quality_gates: [QG-INTAKE]
        approval_rules: [human-gate]
        next_agents: []
        cannot: [invent]
        human_approval_required: [scope]
        escalation_conditions: [missing-input]
        success_criteria: [output-exists]
        failure_conditions: [missing-output]
        """,
    )
    write_file(tmp_path, "core/QUALITY.md", "# Quality")
    write_file(tmp_path, "playbooks/intake.md", "# Intake")
    write_file(tmp_path, "knowledge/foundations.md", "# Foundations")
    write_file(
        tmp_path,
        "workflows/software-project.yaml",
        """
        id: software-project
        name: Software Project
        version: 0.1.0
        description: Fluxo mínimo para testes.
        applicable_project_types: [software]
        required_context: [project.yaml]
        stages:
          - id: intake
            mode: sequential
            workflow: project-intake
        stage_dependencies:
          intake: []
        assigned_agents:
          intake: [business-analyst]
        stage_quality_gates:
          intake: QG-INTAKE
        conditions: []
        quality_gates: [QG-INTAKE]
        human_approvals: []
        artifacts: [project-brief]
        failure_handling:
          validation_error: blocked
        completion_criteria:
          - Fluxo preparado
        """,
    )
    write_file(
        tmp_path,
        "projects/sample/project.yaml",
        """
        id: sample
        name: Sample
        version: 0.1.0
        status: active
        project_type: software
        workflow_id: software-project
        data_classification: internal
        sprint:
          id: sprint-2
          objective: Executar teste sequencial.
          status: running
        """,
    )
    write_file(tmp_path, "projects/sample/README.md", "# Sample")
    write_file(tmp_path, "projects/sample/intake/brief.md", "# Brief")
    write_file(
        tmp_path,
        "projects/sample/business-analysis/scope.md",
        "# Scope\n\nEscopo confirmado para teste.",
    )
    return tmp_path
