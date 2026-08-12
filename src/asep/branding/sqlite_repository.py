"""SQLite persistence for the singleton runtime branding override."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from asep.branding.errors import (
    BrandingStorageReadError,
    BrandingStorageWriteError,
    InvalidBrandingStorageFormatError,
)
from asep.branding.models import BrandingSettings
from asep.branding.serialization import BRANDING_STORAGE_VERSION, BrandingCodec
from asep.sqlite import SQLiteDatabase, SQLiteStorageError

_BRANDING_KEY = "runtime"


class SQLiteBrandingRepository:
    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def get(self) -> BrandingSettings | None:
        try:
            with self._database.connect() as connection:
                row = connection.execute(
                    "SELECT version, payload FROM branding_settings WHERE id = ?",
                    (_BRANDING_KEY,),
                ).fetchone()
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise BrandingStorageReadError(
                "Falha ao ler branding no SQLite.", path=self._database.path
            ) from exc
        if row is None:
            return None
        return self._deserialize(row["version"], row["payload"])

    def replace(self, settings: BrandingSettings) -> None:
        payload = self._serialize(settings)
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO branding_settings (id, version, payload)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        version = excluded.version,
                        payload = excluded.payload
                    """,
                    (_BRANDING_KEY, BRANDING_STORAGE_VERSION, payload),
                )
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise BrandingStorageWriteError(
                "Falha ao persistir branding no SQLite.", path=self._database.path
            ) from exc

    def _serialize(self, settings: BrandingSettings) -> str:
        try:
            return json.dumps(
                BrandingCodec.encode(settings),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise BrandingStorageWriteError(
                "Falha ao serializar branding para SQLite.", path=self._database.path
            ) from exc

    def _deserialize(self, version: Any, payload: Any) -> BrandingSettings:
        try:
            document = json.loads(payload)
            return BrandingCodec.decode_document(
                {"version": version, "branding": document}
            )
        except InvalidBrandingStorageFormatError as exc:
            raise type(exc)(exc.message, path=self._database.path) from exc
        except (json.JSONDecodeError, TypeError) as exc:
            raise InvalidBrandingStorageFormatError(
                "Branding no SQLite possui formato inválido.",
                path=self._database.path,
            ) from exc


__all__ = ["SQLiteBrandingRepository"]
