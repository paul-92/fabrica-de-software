"""Atomic JSON persistence for the singleton runtime branding override."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from asep.branding.errors import (
    BrandingStorageReadError,
    BrandingStorageWriteError,
    InvalidBrandingStorageFormatError,
)
from asep.branding.models import BrandingSettings
from asep.branding.serialization import BrandingCodec


class FileBrandingRepository:
    """Uses atomic replacement; concurrent multi-process updates can still be lost."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._settings = self._load()

    def get(self) -> BrandingSettings | None:
        return None if self._settings is None else self._copy(self._settings)

    def replace(self, settings: BrandingSettings) -> None:
        detached = self._copy(settings)
        self._write(detached)
        self._settings = detached

    def _load(self) -> BrandingSettings | None:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise BrandingStorageReadError(
                "Falha ao ler branding persistido.", path=self._path
            ) from exc
        if not raw.strip():
            raise InvalidBrandingStorageFormatError(
                "Arquivo de branding persistido está vazio.", path=self._path
            )
        try:
            document = json.loads(raw, parse_constant=self._reject_constant)
            return BrandingCodec.decode_document(document)
        except InvalidBrandingStorageFormatError as exc:
            if exc.path is not None:
                raise
            raise type(exc)(exc.message, path=self._path) from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise InvalidBrandingStorageFormatError(
                "Arquivo de branding contém JSON inválido.", path=self._path
            ) from exc

    def _write(self, settings: BrandingSettings) -> None:
        try:
            content = json.dumps(
                BrandingCodec.encode_document(settings),
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise BrandingStorageWriteError(
                "Falha ao serializar branding.", path=self._path
            ) from exc
        temporary: Path | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".asep-branding-",
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
            raise BrandingStorageWriteError(
                "Falha ao persistir branding.", path=self._path
            ) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _copy(settings: BrandingSettings) -> BrandingSettings:
        return BrandingCodec.decode(BrandingCodec.encode(settings))

    @staticmethod
    def _reject_constant(value: str) -> None:
        raise ValueError(f"Constante JSON inválida: {value}")


__all__ = ["FileBrandingRepository"]
