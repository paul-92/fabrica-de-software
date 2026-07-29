"""Porta de persistência neutra para Runs."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from asep.runs.models import Run


@runtime_checkable
class RunRepository(Protocol):
    def save(self, run: Run) -> None: ...

    def get(self, run_id: str) -> Run: ...

    def list(self) -> tuple[Run, ...]: ...
