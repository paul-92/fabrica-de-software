"""Implementação persistente em JSON do RunRepository."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from asep.errors import RunNotFoundError
from asep.runs.errors import (
    InvalidRunStorageFormatError,
    RunStorageReadError,
    RunStorageWriteError,
)
from asep.runs.models import Run
from asep.runs.serialization import RunCodec

RUN_STORAGE_VERSION = "1.0"


class FileRunRepository:
    """Mantém snapshots de Runs em um único arquivo JSON atômico."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._runs = self._load_or_initialize()

    def save(self, run: Run) -> None:
        updated = dict(self._runs)
        updated[run.id] = self._copy(run)
        ordered = tuple(
            sorted(
                updated.values(),
                key=lambda item: (item.started_at, item.id),
            )
        )
        self._write_runs(ordered)
        self._runs = {item.id: item for item in ordered}

    def get(self, run_id: str) -> Run:
        try:
            run = self._runs[run_id]
        except KeyError as exc:
            raise RunNotFoundError(
                f"Run não encontrado no repositório: {run_id}"
            ) from exc
        return self._copy(run)

    def list(self) -> tuple[Run, ...]:
        return tuple(
            self._copy(run)
            for run in sorted(
                self._runs.values(),
                key=lambda item: (item.started_at, item.id),
            )
        )

    def _load_or_initialize(self) -> dict[str, Run]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._write_runs(())
            return {}
        except OSError as exc:
            raise RunStorageReadError(
                "Falha ao ler o arquivo de Runs.",
                path=self._path,
            ) from exc

        if not raw.strip():
            return {}
        try:
            document = json.loads(
                raw,
                parse_constant=self._reject_non_json_constant,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise InvalidRunStorageFormatError(
                "Arquivo de Runs contém JSON inválido.",
                path=self._path,
            ) from exc
        runs = self._decode_document(document)
        return {run.id: run for run in runs}

    def _decode_document(self, document: Any) -> tuple[Run, ...]:
        if not isinstance(document, dict):
            raise InvalidRunStorageFormatError(
                "Documento de Runs deve ser um objeto.",
                path=self._path,
            )
        if set(document) != {"version", "runs"}:
            raise InvalidRunStorageFormatError(
                "Envelope do arquivo de Runs é inválido.",
                path=self._path,
            )
        if document["version"] != RUN_STORAGE_VERSION:
            raise InvalidRunStorageFormatError(
                "Versão do arquivo de Runs não suportada.",
                path=self._path,
            )
        records = document["runs"]
        if not isinstance(records, list):
            raise InvalidRunStorageFormatError(
                "Campo runs do arquivo deve ser uma lista.",
                path=self._path,
            )

        runs: list[Run] = []
        identifiers: set[str] = set()
        for record in records:
            if not isinstance(record, dict):
                raise InvalidRunStorageFormatError(
                    "Registro de Run deve ser um objeto.",
                    path=self._path,
                )
            try:
                run = RunCodec.decode(record)
            except InvalidRunStorageFormatError as exc:
                raise InvalidRunStorageFormatError(
                    "Arquivo contém Run inválido.",
                    path=self._path,
                ) from exc
            if run.id in identifiers:
                raise InvalidRunStorageFormatError(
                    "Arquivo contém IDs de Run duplicados.",
                    path=self._path,
                )
            identifiers.add(run.id)
            runs.append(run)
        return tuple(runs)

    def _write_runs(self, runs: tuple[Run, ...]) -> None:
        document = {
            "version": RUN_STORAGE_VERSION,
            "runs": [RunCodec.encode(run) for run in runs],
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
            raise RunStorageWriteError(
                "Falha ao serializar Runs.",
                path=self._path,
            ) from exc

        temporary: Path | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".asep-runs-",
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
            raise RunStorageWriteError(
                "Falha ao persistir o arquivo de Runs.",
                path=self._path,
            ) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _copy(run: Run) -> Run:
        return Run.model_validate(run.model_dump(mode="json"))

    @staticmethod
    def _reject_non_json_constant(value: str) -> None:
        raise ValueError(f"Constante JSON inválida: {value}")
