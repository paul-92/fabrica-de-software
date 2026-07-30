"""Codec JSON estável para MemoryEntry."""

from typing import Any, Mapping

from asep.memory.models import MemoryEntry


class MemoryEntryCodec:
    @staticmethod
    def encode(entry: MemoryEntry) -> dict[str, Any]:
        return entry.model_dump(mode="json")

    @staticmethod
    def decode(document: Mapping[str, Any]) -> MemoryEntry:
        return MemoryEntry.model_validate(document)


__all__ = ["MemoryEntryCodec"]

