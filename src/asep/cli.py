"""Interface de linha de comando da ASEP."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import typer
from rich.console import Console
from rich.table import Table

from asep.errors import AsepError
from asep.logging_config import configure_logging
from asep.orchestrator.service import Orchestrator
from asep.execution.state import RunLocator

app = typer.Typer(
    name="asep",
    help="AI Software Engineering Platform.",
    no_args_is_help=True,
)
console = Console()
error_console = Console(stderr=True)


@app.callback()
def root() -> None:
    """Inicializa a interface de linha de comando da ASEP."""


@app.command()
def run(
    project: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Diretório do projeto ASEP.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Logs detalhados."),
) -> None:
    """Executa o workflow sequencial aprovado para o projeto."""
    run_id = str(uuid4())
    try:
        log_path = project / "logs" / "runs" / f"{run_id}.jsonl"
        logger = configure_logging(
            project, run_id=run_id, verbose=verbose, log_path=log_path
        )
    except AsepError as exc:
        error_console.print(f"[bold red]{exc.code}[/bold red] {exc}")
        error_console.print(f"Próxima ação: {exc.next_action}")
        raise typer.Exit(code=exc.exit_code) from exc
    try:
        result = Orchestrator().execute(project, run_id, logger)
    except AsepError as exc:
        logger.error(
            exc.message,
            extra={"event_type": "orchestrator.failed"},
        )
        error_console.print(f"[bold red]{exc.code}[/bold red] {exc}")
        error_console.print(f"Próxima ação: {exc.next_action}")
        raise typer.Exit(code=exc.exit_code) from exc

    table = Table(title="ASEP — execução sequencial")
    table.add_column("Item")
    table.add_column("Valor")
    table.add_row("Projeto", result.project_id)
    table.add_row("Workflow", result.workflow_id)
    table.add_row("Run ID", result.run_id)
    table.add_row("Estado", result.status)
    table.add_row("Etapa atual", result.current_stage or "-")
    table.add_row("Etapas concluídas", str(len(result.completed_stages)))
    table.add_row("Estado persistido", str(result.state_path))
    table.add_row("Artefatos", str(result.artifacts_path))
    console.print(table)
    console.print(f"[green]Execução encerrada com estado {result.status}.[/green]")


@app.command()
def resume(
    run_id: str = typer.Argument(..., help="UUID v4 da execução a retomar."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Logs detalhados."),
) -> None:
    """Retoma uma execução interrompida entre etapas."""
    logger = None
    try:
        state_path = RunLocator().locate(Path.cwd(), run_id)
        project = state_path.resolve().parents[3]
        log_path = project / "logs" / "runs" / f"{run_id}.jsonl"
        logger = configure_logging(
            project, run_id=run_id, verbose=verbose, log_path=log_path
        )
        result = Orchestrator().resume(state_path, logger)
    except AsepError as exc:
        if logger is not None:
            logger.error(
                exc.message,
                extra={"event_type": "orchestrator.failed"},
            )
        error_console.print(f"[bold red]{exc.code}[/bold red] {exc}")
        error_console.print(f"Próxima ação: {exc.next_action}")
        raise typer.Exit(code=exc.exit_code) from exc
    table = Table(title="ASEP — execução retomada")
    table.add_column("Item")
    table.add_column("Valor")
    table.add_row("Run ID", result.run_id)
    table.add_row("Projeto", result.project_id)
    table.add_row("Workflow", result.workflow_id)
    table.add_row("Estado", result.status)
    table.add_row("Etapas concluídas", str(len(result.completed_stages)))
    console.print(table)


def main() -> None:
    """Entry point explícito para execução como módulo."""
    app()


if __name__ == "__main__":
    main()
