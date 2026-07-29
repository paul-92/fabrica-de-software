"""Representação interna mínima do processo BPMN exportado."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BpmnNodeKind(StrEnum):
    START_EVENT = "startEvent"
    END_EVENT = "endEvent"
    TASK = "task"
    PARALLEL_GATEWAY = "parallelGateway"


@dataclass(frozen=True)
class BpmnNode:
    element_id: str
    kind: BpmnNodeKind
    name: str | None = None


@dataclass(frozen=True)
class BpmnFlow:
    flow_id: str
    source_ref: str
    target_ref: str
    name: str | None = None


@dataclass(frozen=True)
class BpmnProcessModel:
    nodes: tuple[BpmnNode, ...]
    flows: tuple[BpmnFlow, ...]
