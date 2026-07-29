"""Persistência atômica e idempotente de pacotes de execução."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from asep.execution_package.models import (
    ExecutionPackage,
    ExecutionPackageFile,
    ExecutionPackageResult,
)
from asep.execution_package.serializer import ExecutionPackageSerializer


class ExecutionPackageWriter:
    def __init__(
        self,
        serializer: ExecutionPackageSerializer | None = None,
    ) -> None:
        self._serializer = serializer or ExecutionPackageSerializer()

    def write(
        self, package: ExecutionPackage, project_path: Path
    ) -> ExecutionPackageResult:
        package_path = (
            project_path.resolve()
            / ".asep"
            / "runs"
            / package.manifest.run_id
            / "packages"
            / package.manifest.stage_id
        )
        package_path.mkdir(parents=True, exist_ok=True)
        files: list[ExecutionPackageFile] = []
        written: list[str] = []
        unchanged: list[str] = []

        for serialized in self._serializer.serialize(package):
            target = package_path / serialized.name
            files.append(ExecutionPackageFile(name=serialized.name, path=target))
            if target.is_file() and target.read_bytes() == serialized.content:
                unchanged.append(serialized.name)
                continue
            self._write_atomic(target, serialized.content)
            written.append(serialized.name)

        return ExecutionPackageResult(
            package_path=package_path,
            files=tuple(files),
            written_files=tuple(written),
            unchanged_files=tuple(unchanged),
        )

    @staticmethod
    def _write_atomic(target: Path, content: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".asep-package-",
                suffix=".tmp",
                dir=target.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(content)
            os.replace(temporary_path, target)
        except OSError:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
