"""Atomic JSON persistence for Quality Gate results."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from asep.quality_results.errors import (
    DuplicateQualityGateResultError,
    InvalidQualityGateResultStorageFormatError,
    QualityGateResultStorageReadError,
    QualityGateResultStorageWriteError,
)
from asep.quality_results.in_memory import result_key, result_order
from asep.quality_results.models import StoredQualityGateResult
from asep.quality_results.serialization import QualityGateResultCodec

QUALITY_GATE_RESULT_STORAGE_VERSION = "1.0"


class FileQualityGateResultRepository:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._results = self._load_or_initialize()

    def record(self, result: StoredQualityGateResult) -> None:
        key = result_key(result)
        if key in self._results:
            raise DuplicateQualityGateResultError(
                "Quality Gate result duplicado: " + "/".join(key)
            )
        updated = dict(self._results)
        updated[key] = self._copy(result)
        ordered = tuple(sorted(updated.values(), key=result_order))
        self._write(ordered)
        self._results = {result_key(item): item for item in ordered}

    def list_by_run(self, run_id: str) -> tuple[StoredQualityGateResult, ...]:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id da consulta não pode ser vazio")
        return tuple(
            self._copy(item)
            for item in sorted(
                (item for item in self._results.values() if item.run_id == run_id),
                key=result_order,
            )
        )

    def _load_or_initialize(
        self,
    ) -> dict[tuple[str, str, str], StoredQualityGateResult]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._write(())
            return {}
        except OSError as exc:
            raise QualityGateResultStorageReadError(
                "Falha ao ler Quality Gate results.", path=self._path
            ) from exc
        if not raw.strip():
            raise InvalidQualityGateResultStorageFormatError(
                "Arquivo de Quality Gate results vazio.", path=self._path
            )
        try:
            document = json.loads(raw, parse_constant=self._reject_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise InvalidQualityGateResultStorageFormatError(
                "Arquivo de Quality Gate results contém JSON inválido.",
                path=self._path,
            ) from exc
        if (
            not isinstance(document, dict)
            or set(document) != {"version", "results"}
            or document.get("version") != QUALITY_GATE_RESULT_STORAGE_VERSION
            or not isinstance(document.get("results"), list)
        ):
            raise InvalidQualityGateResultStorageFormatError(
                "Envelope de Quality Gate results inválido.", path=self._path
            )
        results: dict[tuple[str, str, str], StoredQualityGateResult] = {}
        for raw_result in document["results"]:
            if not isinstance(raw_result, dict):
                raise InvalidQualityGateResultStorageFormatError(
                    "Quality Gate result deve ser um objeto.", path=self._path
                )
            try:
                result = QualityGateResultCodec.decode(raw_result)
            except InvalidQualityGateResultStorageFormatError as exc:
                raise InvalidQualityGateResultStorageFormatError(
                    "Arquivo contém Quality Gate result inválido.", path=self._path
                ) from exc
            key = result_key(result)
            if key in results:
                raise InvalidQualityGateResultStorageFormatError(
                    "Arquivo contém Quality Gate results duplicados.", path=self._path
                )
            results[key] = result
        return results

    def _write(self, results: tuple[StoredQualityGateResult, ...]) -> None:
        try:
            content = json.dumps(
                {
                    "version": QUALITY_GATE_RESULT_STORAGE_VERSION,
                    "results": [QualityGateResultCodec.encode(item) for item in results],
                },
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise QualityGateResultStorageWriteError(
                "Falha ao serializar Quality Gate results.", path=self._path
            ) from exc
        temporary: Path | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n",
                prefix=".asep-quality-gates-", suffix=".tmp",
                dir=self._path.parent, delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
            temporary = None
        except OSError as exc:
            raise QualityGateResultStorageWriteError(
                "Falha ao persistir Quality Gate results.", path=self._path
            ) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _copy(result: StoredQualityGateResult) -> StoredQualityGateResult:
        return QualityGateResultCodec.decode(QualityGateResultCodec.encode(result))

    @staticmethod
    def _reject_constant(value: str) -> None:
        raise ValueError(f"Constante JSON inválida: {value}")


__all__ = ["FileQualityGateResultRepository"]
