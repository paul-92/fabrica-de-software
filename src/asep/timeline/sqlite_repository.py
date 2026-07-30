"""Implementação SQLite do TimelineRepository."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from asep.sqlite import SQLiteDatabase, SQLiteStorageError
from asep.timeline.errors import (
    DuplicateTimelineEventError,
    InvalidTimelineStorageFormatError,
    TimelineStorageReadError,
    TimelineStorageWriteError,
)
from asep.timeline.models import TimelineEvent
from asep.timeline.serialization import TimelineEventCodec


class SQLiteTimelineRepository:
    """Persiste eventos append-only em uma tabela SQLite."""

    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def append(self, event: TimelineEvent) -> None:
        payload = self._serialize(event)
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO timeline_events
                        (id, run_id, timestamp, payload)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        event.id,
                        event.run_id,
                        event.timestamp.isoformat(),
                        payload,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateTimelineEventError(
                f"Evento de Timeline duplicado: {event.id}"
            ) from exc
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise TimelineStorageWriteError(
                "Falha ao persistir evento no SQLite.",
                path=self._database.path,
            ) from exc

    def list_by_run(self, run_id: str) -> tuple[TimelineEvent, ...]:
        if not run_id.strip():
            raise ValueError("run_id da consulta não pode ser vazio")
        try:
            with self._database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT payload
                    FROM timeline_events
                    WHERE run_id = ?
                    """,
                    (run_id,),
                ).fetchall()
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise TimelineStorageReadError(
                "Falha ao consultar Timeline no SQLite.",
                path=self._database.path,
            ) from exc
        events = tuple(self._deserialize(row["payload"]) for row in rows)
        return tuple(
            sorted(events, key=lambda item: (item.timestamp, item.id))
        )

    def _serialize(self, event: TimelineEvent) -> str:
        try:
            return json.dumps(
                TimelineEventCodec.encode(event),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise TimelineStorageWriteError(
                "Falha ao serializar Timeline para SQLite.",
                path=self._database.path,
            ) from exc

    def _deserialize(self, payload: Any) -> TimelineEvent:
        try:
            document = json.loads(payload)
            if not isinstance(document, dict):
                raise TypeError
            return TimelineEventCodec.decode(document)
        except (
            json.JSONDecodeError,
            TypeError,
            InvalidTimelineStorageFormatError,
        ) as exc:
            raise InvalidTimelineStorageFormatError(
                "Evento no SQLite possui formato inválido.",
                path=self._database.path,
            ) from exc
