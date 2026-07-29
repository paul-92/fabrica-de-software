import json
import logging
from pathlib import Path

from asep.logging_config import configure_logging


def test_json_log_contains_run_id(tmp_path: Path) -> None:
    logger = configure_logging(tmp_path, run_id="run-test")
    logger.info("evento", extra={"event_type": "test.completed"})
    for handler in logger.handlers:
        handler.flush()

    line = (tmp_path / "logs/asep-runtime.jsonl").read_text(
        encoding="utf-8"
    )
    payload = json.loads(line)

    assert payload["run_id"] == "run-test"
    assert payload["event_type"] == "test.completed"
    assert payload["level"] == "INFO"
