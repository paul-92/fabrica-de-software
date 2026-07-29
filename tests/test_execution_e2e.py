import re
from pathlib import Path

import yaml
from typer.testing import CliRunner

from asep.cli import app


def test_cli_end_to_end_persists_state_artifact_gate_and_log(
    sample_repository: Path,
) -> None:
    project = sample_repository / "projects/sample"

    result = CliRunner().invoke(app, ["run", str(project)])

    assert result.exit_code == 0, result.output
    run_id = re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        result.output,
    ).group(0)
    state_path = project / ".asep/runs" / run_id / "state.yaml"
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    artifacts = project / "artifacts/runs" / run_id

    assert state["execution_status"] == "completed"
    assert state["stages"][0]["status"] == "completed"
    assert (artifacts / "business-analysis/execution-summary.md").is_file()
    assert (artifacts / "quality-gates/intake-result.yaml").is_file()
    log = (project / "logs/runs" / f"{run_id}.jsonl").read_text(
        encoding="utf-8"
    )
    assert run_id in log
    assert '"event": "run_completed"' in log


def test_cli_resume_keeps_run_id_and_does_not_repeat_completed_stage(
    sample_repository: Path, monkeypatch
) -> None:
    project = sample_repository / "projects/sample"
    scope = project / "business-analysis/scope.md"
    scope.unlink()
    monkeypatch.chdir(sample_repository)

    blocked = CliRunner().invoke(app, ["run", str(project)])
    assert blocked.exit_code == 0, blocked.output
    run_id = re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        blocked.output,
    ).group(0)
    assert "blocked" in blocked.output

    scope.parent.mkdir(parents=True, exist_ok=True)
    scope.write_text("# Scope\n\nAgora confirmado.", encoding="utf-8")
    resumed = CliRunner().invoke(app, ["resume", run_id])

    assert resumed.exit_code == 0, resumed.output
    state_path = project / ".asep/runs" / run_id / "state.yaml"
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    assert state["execution_status"] == "completed"
    assert state["stages"][0]["attempts"] == 2
    assert resumed.output.count(run_id) == 1

    repeated = CliRunner().invoke(app, ["resume", run_id])
    assert repeated.exit_code == 6
    assert "RUN_NOT_RESUMABLE" in repeated.output
