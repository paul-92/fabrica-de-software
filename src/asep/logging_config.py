"""Logging estruturado para terminal e arquivo local."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from asep.errors import ConfigurationError


class RunContextFilter(logging.Filter):
    """Anexa o identificador de execução a todos os registros."""

    def __init__(self, run_id: str) -> None:
        super().__init__()
        self._run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self._run_id
        return True


class JsonFormatter(logging.Formatter):
    """Serializa campos seguros de um LogRecord em JSON Lines."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "occurred_at": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "run_id",
            "event_type",
            "project_id",
            "workflow_id",
            "stage_id",
            "agent_id",
            "elapsed_seconds",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        event_type = payload.get("event_type")
        if event_type is not None:
            payload["event"] = event_type
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    project_path: Path,
    *,
    run_id: str,
    verbose: bool = False,
    log_path: Path | None = None,
) -> logging.Logger:
    """Configura logger idempotente e grava JSONL no diretório do projeto."""
    logger = logging.getLogger("asep")
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    context_filter = RunContextFilter(run_id)
    console.addFilter(context_filter)
    logger.addHandler(console)

    target = log_path or project_path / "logs" / "asep-runtime.jsonl"
    log_dir = target.parent
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(target, encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(
            f"Não foi possível preparar o log: {exc}", path=log_dir
        ) from exc
    file_handler.setFormatter(JsonFormatter())
    file_handler.addFilter(context_filter)
    logger.addHandler(file_handler)
    return logger
