from pathlib import Path

from typer.testing import CliRunner

from asep.cli import app


def test_cli_run_prepares_project(sample_repository: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["run", str(sample_repository / "projects/sample")],
    )

    assert result.exit_code == 0, result.output
    assert "sample" in result.output
    assert "software-project" in result.output
    assert "completed" in result.output
    assert "Run ID" in result.output


def test_cli_rejects_missing_project() -> None:
    result = CliRunner().invoke(app, ["run", "missing-project"])

    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_cli_uses_validation_exit_code(sample_repository: Path) -> None:
    manifest = sample_repository / "projects/sample/project.yaml"
    manifest.write_text("id: [", encoding="utf-8")

    result = CliRunner().invoke(app, ["run", str(manifest.parent)])

    assert result.exit_code == 3
    assert "PROJECT_INVALID" in result.output
    assert "Próxima ação:" in result.output
