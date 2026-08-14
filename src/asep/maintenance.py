"""Small filesystem maintenance gate shared by the API and operations tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from uuid import uuid4


class MaintenanceActiveError(RuntimeError):
    pass


class MaintenanceTimeoutError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MutationLease:
    path: Path

    def release(self) -> None:
        self.path.unlink(missing_ok=True)


class MaintenanceGate:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.active = self.root / "active"
        self.marker = self.root / "maintenance"
        self.active.mkdir(parents=True, exist_ok=True)

    def begin_mutation(self) -> MutationLease:
        if self.marker.exists():
            raise MaintenanceActiveError("ASEP is in maintenance mode.")
        token = self.active / str(uuid4())
        token.touch(exist_ok=False)
        if self.marker.exists():
            token.unlink(missing_ok=True)
            raise MaintenanceActiveError("ASEP is in maintenance mode.")
        return MutationLease(token)

    def enter(self, timeout_seconds: float = 30.0) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.marker.touch(exist_ok=False)
        except FileExistsError as exc:
            raise MaintenanceActiveError("Maintenance mode is already active.") from exc
        deadline = time.monotonic() + timeout_seconds
        while any(self.active.iterdir()):
            if time.monotonic() >= deadline:
                self.marker.unlink(missing_ok=True)
                raise MaintenanceTimeoutError("Active mutations did not drain before timeout.")
            time.sleep(0.05)

    def release(self) -> None:
        self.marker.unlink(missing_ok=True)


__all__ = ["MaintenanceActiveError", "MaintenanceGate", "MaintenanceTimeoutError", "MutationLease"]
