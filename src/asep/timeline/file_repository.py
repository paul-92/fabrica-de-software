"""Implementação persistente em JSON do TimelineRepository."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from asep.timeline.errors import (
    DuplicateTimelineEventError,
    InvalidTimelineStorageFormatError,
    TimelineStorageReadError,
    TimelineStorageWriteError,
)
from asep.timeline.models import TimelineEvent
from asep.timeline.serialization import TimelineEventCodec

TIMELINE_STORAGE_VERSION = "1.0"


class FileTimelineRepository:
    """Persiste uma Timeline append-only em um único arquivo JSON."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def append(self, event: TimelineEvent) -> None:
        events = list(self._read_events())
        if any(stored.id == event.id for stored in events):
            raise DuplicateTimelineEventError(
                f"Evento de Timeline duplicado: {event.id}"
            )
        events.append(
            TimelineEvent.model_validate(event.model_dump(mode="json"))
        )
        self._write_events(tuple(events))

    def list_by_run(self, run_id: str) -> tuple[TimelineEvent, ...]:
        if not run_id.strip():
            raise ValueError("run_id da consulta não pode ser vazio")
        return tuple(
            TimelineEvent.model_validate(event.model_dump(mode="json"))
            for event in sorted(
                (
                    event
                    for event in self._read_events()
                    if event.run_id == run_id
                ),
                key=lambda item: item.timestamp,
            )
        )

    def _read_events(self) -> tuple[TimelineEvent, ...]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise TimelineStorageReadError(
                "Falha ao ler o arquivo de Timeline.",
                path=self._path,
            ) from exc

        if not raw.strip():
            raise InvalidTimelineStorageFormatError(
                "Arquivo de Timeline vazio.",
                path=self._path,
            )
        try:
            document = json.loads(
                raw,
                parse_constant=self._reject_non_json_constant,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise InvalidTimelineStorageFormatError(
                "Arquivo de Timeline contém JSON inválido.",
                path=self._path,
            ) from exc
        return self._decode_document(document)

    def _decode_document(self, document: Any) -> tuple[TimelineEvent, ...]:
        if not isinstance(document, dict):
            raise InvalidTimelineStorageFormatError(
                "Documento de Timeline deve ser um objeto.",
                path=self._path,
            )
        if set(document) != {"version", "events"}:
            raise InvalidTimelineStorageFormatError(
                "Envelope do arquivo de Timeline é inválido.",
                path=self._path,
            )
        if document["version"] != TIMELINE_STORAGE_VERSION:
            raise InvalidTimelineStorageFormatError(
                "Versão do arquivo de Timeline não suportada.",
                path=self._path,
            )
        records = document["events"]
        if not isinstance(records, list):
            raise InvalidTimelineStorageFormatError(
                "Campo events do arquivo de Timeline deve ser uma lista.",
                path=self._path,
            )
        events: list[TimelineEvent] = []
        identifiers: set[str] = set()
        for record in records:
            if not isinstance(record, dict):
                raise InvalidTimelineStorageFormatError(
                    "Registro de Timeline deve ser um objeto.",
                    path=self._path,
                )
            try:
                event = TimelineEventCodec.decode(record)
            except InvalidTimelineStorageFormatError as exc:
                raise InvalidTimelineStorageFormatError(
                    "Arquivo contém evento de Timeline inválido.",
                    path=self._path,
                ) from exc
            if event.id in identifiers:
                raise InvalidTimelineStorageFormatError(
                    "Arquivo contém IDs de evento duplicados.",
                    path=self._path,
                )
            identifiers.add(event.id)
            events.append(event)
        return tuple(events)

    def _write_events(self, events: tuple[TimelineEvent, ...]) -> None:
        document = {
            "version": TIMELINE_STORAGE_VERSION,
            "events": [
                TimelineEventCodec.encode(event) for event in events
            ],
        }
        try:
            content = json.dumps(
                document,
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise TimelineStorageWriteError(
                "Falha ao serializar eventos da Timeline.",
                path=self._path,
            ) from exc

        temporary: Path | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".asep-timeline-",
                suffix=".tmp",
                dir=self._path.parent,
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
            temporary = None
        except OSError as exc:
            raise TimelineStorageWriteError(
                "Falha ao persistir o arquivo de Timeline.",
                path=self._path,
            ) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _reject_non_json_constant(value: str) -> None:
        raise ValueError(f"Constante JSON inválida: {value}")
