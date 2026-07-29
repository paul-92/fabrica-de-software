"""Interface de linha de comando da ASEP."""

from __future__ import annotations

import os
import tempfile
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

import typer
from rich.console import Console
from rich.table import Table

from asep.application.query_composition import get_run_query_service
from asep.cli_history import format_run, format_runs, format_timeline
from asep.errors import AsepError, ConfigurationError, ConsistencyError
from asep.execution_graph import ExecutionGraphBuilder
from asep.logging_config import configure_logging
from asep.orchestrator.service import Orchestrator
from asep.execution.state import RunLocator
from asep.exporters import BpmnExporter, JsonExporter, MermaidExporter
from asep.project.loader import ProjectLoader
from asep.registry.loader import RegistryLoader
from asep.runs import RunStatus
from asep.workflow.loader import WorkflowLoader

app = typer.Typer(
    name="asep",
    help="AI Software Engineering Platform.",
    no_args_is_help=True,
)
console = Console()
error_console = Console(stderr=True)
run_query_service_provider = get_run_query_service


class GraphFormat(StrEnum):
    MERMAID = "mermaid"
    BPMN = "bpmn"
    JSON = "json"


@app.callback()
def root() -> None:
    """Inicializa a interface de linha de comando da ASEP."""


@app.command()
def run(
    command_or_project: str = typer.Argument(
        ...,
        metavar="PROJECT|show|timeline",
        help="Diretório do projeto ou subcomando de consulta.",
    ),
    run_id: str | None = typer.Argument(
        None,
        help="Identificador exigido por show e timeline.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Logs detalhados."),
) -> None:
    """Executa PROJECT ou consulta com `run show|timeline RUN_ID`."""
    if command_or_project == "show":
        _show_run(_required_query_run_id(run_id, action="show"))
        return
    if command_or_project == "timeline":
        _show_run_timeline(
            _required_query_run_id(run_id, action="timeline")
        )
        return
    if run_id is not None:
        raise typer.BadParameter(
            "argumento adicional permitido apenas após show ou timeline.",
            param_hint="RUN_ID",
        )
    project = _validated_project_path(command_or_project)
    _execute_project(project, verbose=verbose)


def _execute_project(project: Path, *, verbose: bool) -> None:
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


@app.command("runs")
def list_runs(
    status: RunStatus | None = typer.Option(
        None,
        "--status",
        help="Filtra pelo status exato do Run.",
    ),
) -> None:
    """Lista Runs disponíveis no processo atual."""
    service = run_query_service_provider()
    try:
        runs = (
            service.list_runs()
            if status is None
            else service.list_runs_by_status(status)
        )
    except AsepError as exc:
        _print_expected_error(exc)
    typer.echo(format_runs(runs))


def _show_run(run_id: str) -> None:
    service = run_query_service_provider()
    try:
        selected = service.get_run(_validated_cli_run_id(run_id))
    except AsepError as exc:
        _print_expected_error(exc)
    typer.echo(format_run(selected))


def _show_run_timeline(run_id: str) -> None:
    service = run_query_service_provider()
    try:
        events = service.get_timeline(_validated_cli_run_id(run_id))
    except AsepError as exc:
        _print_expected_error(exc)
    typer.echo(format_timeline(events))


@app.command()
def graph(
    project: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Diretório do projeto ASEP.",
    ),
    output_format: GraphFormat = typer.Option(
        GraphFormat.MERMAID,
        "--format",
        help="Formato textual de saída.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        file_okay=True,
        dir_okay=False,
        resolve_path=False,
        help="Arquivo de destino; omita para usar stdout.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Substitui atomicamente um arquivo de saída existente.",
    ),
) -> None:
    """Gera o grafo estático do workflow no formato solicitado."""
    if force and output is None:
        raise typer.BadParameter("--force requer --output.")
    try:
        loaded_project = ProjectLoader().load(project)
        repository_root = ProjectLoader.find_repository_root(
            loaded_project.path
        )
        registry = RegistryLoader().load(repository_root / "registry")
        workflow_entry = registry.workflows.get(
            loaded_project.definition.workflow_id
        )
        if workflow_entry is None:
            raise ConsistencyError(
                "Workflow do projeto não existe no Registry: "
                f"{loaded_project.definition.workflow_id}"
            )
        workflow = WorkflowLoader().load(workflow_entry, registry)
        execution_graph = ExecutionGraphBuilder().build(
            workflow,
            project_name=loaded_project.definition.name,
        )
        if output_format is GraphFormat.MERMAID:
            content = MermaidExporter().export(execution_graph)
        elif output_format is GraphFormat.BPMN:
            content = BpmnExporter().export(execution_graph)
        elif output_format is GraphFormat.JSON:
            content = JsonExporter().export(execution_graph)
        else:  # pragma: no cover - proteção para formatos futuros
            raise ConfigurationError(
                f"Formato de grafo não suportado: {output_format}"
            )

        if output is None:
            typer.echo(content, nl=False)
            return
        target = output.expanduser().resolve()
        _write_graph_output(target, content, force=force)
        format_name = (
            "Mermaid"
            if output_format is GraphFormat.MERMAID
            else output_format.value.upper()
        )
        typer.echo(
            f"{format_name} graph written to {target}",
            err=True,
        )
    except AsepError as exc:
        error_console.print(f"[bold red]{exc.code}[/bold red] {exc}")
        error_console.print(f"Próxima ação: {exc.next_action}")
        raise typer.Exit(code=exc.exit_code) from exc


def _write_graph_output(
    target: Path,
    content: str,
    *,
    force: bool,
) -> None:
    if target.exists() and not force:
        raise ConfigurationError(
            "Arquivo de saída já existe; use --force para substituir.",
            path=target,
        )

    temporary: Path | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".asep-graph-",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        if force:
            os.replace(temporary, target)
            temporary = None
        else:
            try:
                os.link(temporary, target)
            except FileExistsError as exc:
                raise ConfigurationError(
                    "Arquivo de saída já existe; use --force para substituir.",
                    path=target,
                ) from exc
            temporary.unlink()
            temporary = None
    except ConfigurationError:
        raise
    except OSError as exc:
        raise ConfigurationError(
            f"Falha ao escrever grafo: {exc}",
            path=target,
        ) from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _print_expected_error(error: AsepError) -> None:
    error_console.print(f"[bold red]{error.code}[/bold red] {error}")
    error_console.print(f"Próxima ação: {error.next_action}")
    raise typer.Exit(code=error.exit_code) from error


def _validated_cli_run_id(run_id: str) -> str:
    if not run_id.strip():
        raise typer.BadParameter(
            "run_id não pode ser vazio.",
            param_hint="RUN_ID",
        )
    return run_id


def _required_query_run_id(
    run_id: str | None,
    *,
    action: str,
) -> str:
    if run_id is None:
        raise typer.BadParameter(
            f"run_id é obrigatório para 'run {action}'.",
            param_hint="RUN_ID",
        )
    return _validated_cli_run_id(run_id)


def _validated_project_path(value: str) -> Path:
    project = Path(value).expanduser()
    if not project.exists():
        raise typer.BadParameter(
            f"Directory '{value}' does not exist.",
            param_hint="PROJECT",
        )
    if not project.is_dir():
        raise typer.BadParameter(
            f"Path '{value}' is not a directory.",
            param_hint="PROJECT",
        )
    if not os.access(project, os.R_OK):
        raise typer.BadParameter(
            f"Directory '{value}' is not readable.",
            param_hint="PROJECT",
        )
    return project.resolve()


def main() -> None:
    """Entry point explícito para execução como módulo."""
    app()


if __name__ == "__main__":
    main()
