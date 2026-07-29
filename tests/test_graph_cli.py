from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml
from typer.testing import CliRunner

import asep.cli as cli_module
from asep.cli import app
from asep.exporters import (
    BpmnExportError,
    JsonExportError,
    MermaidExportError,
)

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
NS = {"bpmn": BPMN_NS, "bpmndi": BPMNDI_NS}


def make_parallel_workflow(repository: Path) -> None:
    workflow_path = repository / "workflows/software-project.yaml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    stage_ids = ["architecture", "backend", "frontend", "tests"]
    workflow["stages"] = [
        {
            "id": stage_id,
            "mode": "sequential",
            "workflow": f"{stage_id}-workflow",
        }
        for stage_id in stage_ids
    ]
    workflow["stage_dependencies"] = {
        "architecture": [],
        "backend": ["architecture"],
        "frontend": ["architecture"],
        "tests": ["backend", "frontend"],
    }
    workflow["assigned_agents"] = {
        stage_id: ["business-analyst"] for stage_id in stage_ids
    }
    workflow["stage_quality_gates"] = {
        stage_id: "QG-INTAKE" for stage_id in stage_ids
    }
    workflow_path.write_text(
        yaml.safe_dump(workflow, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    registry_path = repository / "registry/workflows.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registry["workflows"][0]["stages"] = stage_ids
    registry_path.write_text(
        yaml.safe_dump(registry, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def project_path(repository: Path) -> Path:
    return repository / "projects/sample"


def test_graph_command_is_available_in_root_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "graph" in result.stdout


def test_graph_command_help_documents_supported_options() -> None:
    result = CliRunner().invoke(app, ["graph", "--help"])

    assert result.exit_code == 0
    assert "--format" in result.stdout
    assert "--output" in result.stdout
    assert "--force" in result.stdout
    assert "--run-id" not in result.stdout
    assert "mermaid" in result.stdout
    assert "bpmn" in result.stdout
    assert "json" in result.stdout


def test_graph_generates_linear_workflow_on_stdout(
    sample_repository: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        ["graph", str(project_path(sample_repository))],
    )

    assert result.exit_code == 0, result.output
    assert result.stdout.startswith("flowchart TD\n")
    assert '    intake["intake"]\n' in result.stdout
    assert "class intake pending" in result.stdout
    assert "written to" not in result.stdout


def test_graph_generates_parallel_dependencies(
    sample_repository: Path,
) -> None:
    make_parallel_workflow(sample_repository)

    result = CliRunner().invoke(
        app,
        ["graph", str(project_path(sample_repository))],
    )

    assert result.exit_code == 0, result.output
    assert "    architecture --> backend\n" in result.stdout
    assert "    architecture --> frontend\n" in result.stdout
    assert "    backend --> tests\n" in result.stdout
    assert "    frontend --> tests\n" in result.stdout


def test_graph_accepts_explicit_mermaid_format(
    sample_repository: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--format",
            "mermaid",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.startswith("flowchart TD\n")


def test_graph_rejects_invalid_format_without_creating_output(
    sample_repository: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "graph.mmd"

    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--format",
            "plantuml",
            "--output",
            str(target),
        ],
    )

    assert result.exit_code == 2
    assert "plantuml" in result.output
    assert not target.exists()


def test_graph_generates_bpmn_only_on_stdout(
    sample_repository: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--format",
            "bpmn",
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    assert result.stdout.startswith(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
    )
    root = ET.fromstring(result.stdout)
    assert root.tag == f"{{{BPMN_NS}}}definitions"
    assert root.find("bpmn:process", NS) is not None
    assert root.find(".//bpmndi:BPMNDiagram", NS) is not None


def test_graph_writes_deterministic_utf8_bpmn_file(
    sample_repository: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "workflow.any-extension"
    arguments = [
        "graph",
        str(project_path(sample_repository)),
        "--format",
        "bpmn",
        "--output",
        str(target),
    ]

    first = CliRunner().invoke(app, arguments)
    first_content = target.read_bytes()
    target.unlink()
    second = CliRunner().invoke(app, arguments)

    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout == ""
    assert "BPMN graph written to" in first.stderr
    assert first_content == target.read_bytes()
    decoded = first_content.decode("utf-8")
    assert ET.fromstring(decoded).tag == f"{{{BPMN_NS}}}definitions"


def test_graph_bpmn_existing_output_requires_force(
    sample_repository: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "workflow.bpmn"
    target.write_text("original", encoding="utf-8")
    arguments = [
        "graph",
        str(project_path(sample_repository)),
        "--format",
        "bpmn",
        "--output",
        str(target),
    ]

    refused = CliRunner().invoke(app, arguments)
    original_after_refusal = target.read_text(encoding="utf-8")
    replaced = CliRunner().invoke(app, [*arguments, "--force"])

    assert refused.exit_code == 5
    assert original_after_refusal == "original"
    assert replaced.exit_code == 0
    assert target.read_text(encoding="utf-8").startswith(
        '<?xml version="1.0" encoding="UTF-8"?>'
    )
    assert not list(tmp_path.glob(".asep-graph-*.tmp"))


def test_graph_bpmn_export_failure_leaves_no_partial_file(
    sample_repository: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "workflow.bpmn"

    def fail_export(self, execution_graph, options=None):
        raise BpmnExportError("fault injection")

    monkeypatch.setattr(cli_module.BpmnExporter, "export", fail_export)
    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--format",
            "bpmn",
            "--output",
            str(target),
        ],
    )

    assert result.exit_code == 3
    assert "BPMN_EXPORT_ERROR" in result.stderr
    assert not target.exists()
    assert not list(tmp_path.glob(".asep-graph-*.tmp"))


def test_graph_generates_json_only_on_stdout(
    sample_repository: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["version"] == "1.0"
    assert payload["generated_at"] is None
    assert payload["graph"]["nodes"][0]["id"] == "intake"
    assert payload["graph"]["edges"] == []


def test_graph_writes_deterministic_json_file(
    sample_repository: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "graph.json"
    arguments = [
        "graph",
        str(project_path(sample_repository)),
        "--format",
        "json",
        "--output",
        str(target),
    ]

    first = CliRunner().invoke(app, arguments)
    first_content = target.read_bytes()
    target.unlink()
    second = CliRunner().invoke(app, arguments)

    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout == ""
    assert "JSON graph written to" in first.stderr
    assert first_content == target.read_bytes()
    assert json.loads(first_content)["version"] == "1.0"


def test_graph_json_export_failure_leaves_no_partial_file(
    sample_repository: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "graph.json"

    def fail_export(self, execution_graph):
        raise JsonExportError("fault injection")

    monkeypatch.setattr(cli_module.JsonExporter, "export", fail_export)
    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--format",
            "json",
            "--output",
            str(target),
        ],
    )

    assert result.exit_code == 3
    assert "JSON_EXPORT_ERROR" in result.stderr
    assert not target.exists()
    assert not list(tmp_path.glob(".asep-graph-*.tmp"))


def test_graph_writes_utf8_file_and_keeps_stdout_empty(
    sample_repository: Path,
    tmp_path: Path,
) -> None:
    project_manifest = project_path(sample_repository) / "project.yaml"
    project = yaml.safe_load(
        project_manifest.read_text(encoding="utf-8")
    )
    project["name"] = "Projeto Ágil"
    project_manifest.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    target = tmp_path / "workflow.mmd"

    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--output",
            str(target),
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.stdout == ""
    assert "Mermaid graph written to" in result.stderr
    assert target.read_text(encoding="utf-8").startswith("flowchart TD\n")


def test_graph_creates_missing_output_directories(
    sample_repository: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "missing" / "docs" / "workflow.mmd"

    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "-o",
            str(target),
        ],
    )

    assert result.exit_code == 0, result.output
    assert target.is_file()


def test_graph_refuses_existing_file_without_force(
    sample_repository: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "workflow.mmd"
    target.write_text("original", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--output",
            str(target),
        ],
    )

    assert result.exit_code == 5
    assert "CONFIGURATION_INVALID" in result.stderr
    assert "--force" in result.stderr
    assert target.read_text(encoding="utf-8") == "original"


def test_graph_force_atomically_replaces_existing_file(
    sample_repository: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "workflow.mmd"
    target.write_text("original", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--output",
            str(target),
            "--force",
        ],
    )

    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8").startswith("flowchart TD\n")
    assert not list(tmp_path.glob(".asep-graph-*.tmp"))


def test_graph_force_requires_output(
    sample_repository: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        ["graph", str(project_path(sample_repository)), "--force"],
    )

    assert result.exit_code == 2
    assert "--force requer --output" in result.output


def test_graph_rejects_missing_project() -> None:
    result = CliRunner().invoke(app, ["graph", "missing-project"])

    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_graph_reports_unregistered_workflow(
    sample_repository: Path,
) -> None:
    manifest = project_path(sample_repository) / "project.yaml"
    project = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    project["workflow_id"] = "missing-workflow"
    manifest.write_text(
        yaml.safe_dump(project, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["graph", str(project_path(sample_repository))],
    )

    assert result.exit_code == 6
    assert "CONSISTENCY_ERROR" in result.stderr
    assert "missing-workflow" in result.stderr


def test_graph_reports_invalid_workflow(
    sample_repository: Path,
) -> None:
    workflow_path = sample_repository / "workflows/software-project.yaml"
    definition = yaml.safe_load(
        workflow_path.read_text(encoding="utf-8")
    )
    definition["stage_dependencies"]["intake"] = ["missing"]
    workflow_path.write_text(
        yaml.safe_dump(definition, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["graph", str(project_path(sample_repository))],
    )

    assert result.exit_code == 3
    assert "WORKFLOW_INVALID" in result.stderr
    assert "missing" in result.stderr


def test_graph_write_failure_preserves_existing_file_and_cleans_temp(
    sample_repository: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "workflow.mmd"
    target.write_text("original", encoding="utf-8")

    def fail_replace(source, destination):
        raise PermissionError("denied")

    monkeypatch.setattr(cli_module.os, "replace", fail_replace)
    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--output",
            str(target),
            "--force",
        ],
    )

    assert result.exit_code == 5
    assert "CONFIGURATION_INVALID" in result.stderr
    assert target.read_text(encoding="utf-8") == "original"
    assert not list(tmp_path.glob(".asep-graph-*.tmp"))


def test_graph_export_failure_does_not_create_partial_file(
    sample_repository: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "workflow.mmd"

    def fail_export(self, execution_graph, options=None):
        raise MermaidExportError("fault injection")

    monkeypatch.setattr(cli_module.MermaidExporter, "export", fail_export)
    result = CliRunner().invoke(
        app,
        [
            "graph",
            str(project_path(sample_repository)),
            "--output",
            str(target),
        ],
    )

    assert result.exit_code == 3
    assert "MERMAID_EXPORT_ERROR" in result.stderr
    assert not target.exists()


def test_graph_stdout_is_deterministic_and_pipeline_clean(
    sample_repository: Path,
) -> None:
    arguments = ["graph", str(project_path(sample_repository))]

    first = CliRunner().invoke(app, arguments)
    second = CliRunner().invoke(app, arguments)

    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout
    assert first.stderr == second.stderr == ""
    assert first.stdout.count("flowchart TD") == 1
    assert "ASEP" not in first.stdout


def test_graph_does_not_break_existing_cli_commands(
    sample_repository: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        ["run", str(project_path(sample_repository))],
    )

    assert result.exit_code == 0, result.output
    assert "Run ID" in result.output
