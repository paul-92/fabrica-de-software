"""Serialização canônica dos arquivos de um pacote de execução."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import yaml
from pydantic import BaseModel

from asep.execution_package.models import ExecutionPackage


@dataclass(frozen=True, slots=True)
class SerializedPackageFile:
    name: str
    content: bytes


class ExecutionPackageSerializer:
    """Gera todas as representações persistíveis sem acessar o filesystem."""

    def serialize(
        self, package: ExecutionPackage
    ) -> tuple[SerializedPackageFile, ...]:
        return (
            SerializedPackageFile(
                "manifest.yaml",
                self._yaml(package.manifest),
            ),
            SerializedPackageFile("task.md", package.task.encode("utf-8")),
            SerializedPackageFile(
                "context.json",
                self._json_file(package.context),
            ),
            SerializedPackageFile(
                "metadata.json",
                self._json_file(package.metadata),
            ),
            SerializedPackageFile(
                "expected_outputs.json",
                self._json_file(
                    {"expected_outputs": list(package.expected_outputs)}
                ),
            ),
            SerializedPackageFile(
                "constraints.md",
                self._constraints_markdown(package.constraints),
            ),
        )

    @classmethod
    def checksum_text(cls, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @classmethod
    def checksum_json(cls, value: Any) -> str:
        return hashlib.sha256(cls.canonical_json(value)).hexdigest()

    @classmethod
    def canonical_json(cls, value: Any) -> bytes:
        normalized = cls._json_value(value)
        return json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @classmethod
    def _json_file(cls, value: Any) -> bytes:
        normalized = cls._json_value(value)
        return (
            json.dumps(
                normalized,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        return value

    @staticmethod
    def _yaml(value: BaseModel) -> bytes:
        content = yaml.safe_dump(
            value.model_dump(mode="json"),
            allow_unicode=True,
            sort_keys=False,
        )
        return content.encode("utf-8")

    @staticmethod
    def _constraints_markdown(constraints: tuple[str, ...]) -> bytes:
        content = "# Restrições\n\n"
        if constraints:
            content += "\n".join(f"- {item}" for item in constraints) + "\n"
        else:
            content += "Nenhuma restrição adicional.\n"
        return content.encode("utf-8")
