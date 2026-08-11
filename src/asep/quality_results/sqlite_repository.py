"""SQLite persistence for Quality Gate results."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from asep.quality_results.errors import (
    DuplicateQualityGateResultError,
    InvalidQualityGateResultStorageFormatError,
    QualityGateResultStorageReadError,
    QualityGateResultStorageWriteError,
)
from asep.quality_results.models import StoredQualityGateResult
from asep.quality_results.serialization import QualityGateResultCodec
from asep.sqlite import SQLiteDatabase, SQLiteStorageError


class SQLiteQualityGateResultRepository:
    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def record(self, result: StoredQualityGateResult) -> None:
        payload = self._serialize(result)
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO quality_gate_results
                        (run_id, stage_id, gate_id, evaluated_at, payload)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        result.run_id, result.stage_id, result.gate_id,
                        result.evaluated_at.isoformat(), payload,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateQualityGateResultError(
                f"Quality Gate result duplicado: {result.run_id}/"
                f"{result.stage_id}/{result.gate_id}"
            ) from exc
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise QualityGateResultStorageWriteError(
                "Falha ao persistir Quality Gate result no SQLite.",
                path=self._database.path,
            ) from exc

    def list_by_run(self, run_id: str) -> tuple[StoredQualityGateResult, ...]:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id da consulta não pode ser vazio")
        try:
            with self._database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT payload FROM quality_gate_results
                    WHERE run_id = ?
                    ORDER BY stage_id, gate_id, evaluated_at
                    """,
                    (run_id,),
                ).fetchall()
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise QualityGateResultStorageReadError(
                "Falha ao listar Quality Gate results no SQLite.",
                path=self._database.path,
            ) from exc
        return tuple(self._deserialize(row["payload"]) for row in rows)

    def _serialize(self, result: StoredQualityGateResult) -> str:
        try:
            return json.dumps(
                QualityGateResultCodec.encode(result),
                ensure_ascii=False, allow_nan=False, sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise QualityGateResultStorageWriteError(
                "Falha ao serializar Quality Gate result para SQLite.",
                path=self._database.path,
            ) from exc

    def _deserialize(self, payload: Any) -> StoredQualityGateResult:
        try:
            document = json.loads(payload)
            if not isinstance(document, dict):
                raise TypeError
            return QualityGateResultCodec.decode(document)
        except (json.JSONDecodeError, TypeError, InvalidQualityGateResultStorageFormatError) as exc:
            raise InvalidQualityGateResultStorageFormatError(
                "Quality Gate result no SQLite possui formato inválido.",
                path=self._database.path,
            ) from exc


__all__ = ["SQLiteQualityGateResultRepository"]
