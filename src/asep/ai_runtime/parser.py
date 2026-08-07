"""Parsing da saída JSONL oficial de ``codex exec --json``."""

from __future__ import annotations

import json
from typing import Any

from asep.ai_runtime.errors import AIRuntimeInvalidResponseError
from asep.ai_runtime.models import (
    AIRuntimeIdentity,
    AIRuntimeResult,
    AIRuntimeUsage,
)


class CodexJSONLParser:
    """Extrai somente mensagem final, thread id e usage estruturado."""

    def parse(
        self,
        output: str,
        *,
        identity: AIRuntimeIdentity,
    ) -> AIRuntimeResult:
        events = self._events(output, identity.runtime_id)
        message: str | None = None
        thread_id: str | None = None
        usage: AIRuntimeUsage | None = None

        for event in events:
            event_type = event.get("type")
            if event_type == "thread.started":
                candidate = event.get("thread_id")
                if isinstance(candidate, str) and candidate.strip():
                    thread_id = candidate
            elif event_type == "item.completed":
                item = event.get("item")
                if isinstance(item, dict) and item.get("type") == "agent_message":
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        message = text
            elif event_type == "turn.completed":
                usage = self._usage(event.get("usage"), identity.runtime_id)

        if message is None:
            raise AIRuntimeInvalidResponseError(identity.runtime_id)
        metadata = {"thread_id": thread_id} if thread_id is not None else {}
        return AIRuntimeResult(
            output=message,
            identity=identity,
            usage=usage,
            metadata=metadata,
        )

    @staticmethod
    def _events(output: str, runtime_id: str) -> tuple[dict[str, Any], ...]:
        if not output.strip():
            raise AIRuntimeInvalidResponseError(runtime_id)
        events: list[dict[str, Any]] = []
        try:
            for line in output.splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("event is not an object")
                events.append(event)
        except (json.JSONDecodeError, ValueError) as exc:
            raise AIRuntimeInvalidResponseError(runtime_id) from exc
        if not events:
            raise AIRuntimeInvalidResponseError(runtime_id)
        return tuple(events)

    @staticmethod
    def _usage(value: Any, runtime_id: str) -> AIRuntimeUsage | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise AIRuntimeInvalidResponseError(runtime_id)
        input_units = value.get("input_tokens")
        output_units = value.get("output_tokens")
        if not isinstance(input_units, int) or not isinstance(output_units, int):
            raise AIRuntimeInvalidResponseError(runtime_id)
        try:
            return AIRuntimeUsage(
                input_units=input_units,
                output_units=output_units,
                total_units=input_units + output_units,
            )
        except ValueError as exc:
            raise AIRuntimeInvalidResponseError(runtime_id) from exc


__all__ = ["CodexJSONLParser"]
