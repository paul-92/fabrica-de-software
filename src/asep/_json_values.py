"""Validação interna de árvores compostas apenas por valores JSON."""

from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any


def freeze_json(value: Any, *, location: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{location} contém número não finito")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError(f"{location} deve usar apenas chaves string")
        return MappingProxyType(
            {
                key: freeze_json(item, location=f"{location}.{key}")
                for key, item in value.items()
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(
            freeze_json(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        )
    raise ValueError(
        f"{location} contém tipo não serializável: {type(value).__name__}"
    )


def json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: json_value(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, tuple):
        return [json_value(item) for item in value]
    return value
