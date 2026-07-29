"""Layout BPMN DI simples, determinístico e independente de tela."""

from __future__ import annotations

import heapq
from collections import defaultdict
from dataclasses import dataclass

from asep.exporters.bpmn_models import (
    BpmnFlow,
    BpmnNode,
    BpmnNodeKind,
    BpmnProcessModel,
)
from asep.exporters.errors import UnsupportedBpmnGraphError

HORIZONTAL_MARGIN = 60.0
VERTICAL_MARGIN = 60.0
HORIZONTAL_GAP = 100.0
VERTICAL_GAP = 70.0

_DIMENSIONS = {
    BpmnNodeKind.START_EVENT: (36.0, 36.0),
    BpmnNodeKind.END_EVENT: (36.0, 36.0),
    BpmnNodeKind.TASK: (120.0, 80.0),
    BpmnNodeKind.PARALLEL_GATEWAY: (50.0, 50.0),
}


@dataclass(frozen=True)
class Bounds:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class PositionedFlow:
    flow: BpmnFlow
    waypoints: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class BpmnLayout:
    bounds: dict[str, Bounds]
    flows: tuple[PositionedFlow, ...]


class BpmnLayoutEngine:
    def layout(self, model: BpmnProcessModel) -> BpmnLayout:
        levels = self._levels(model)
        by_level: dict[int, list[BpmnNode]] = defaultdict(list)
        for node in model.nodes:
            by_level[levels[node.element_id]].append(node)

        widest = max((len(nodes) for nodes in by_level.values()), default=1)
        bounds: dict[str, Bounds] = {}
        for level in sorted(by_level):
            nodes = sorted(
                by_level[level], key=lambda item: item.element_id
            )
            level_width = max(
                _DIMENSIONS[node.kind][0] for node in nodes
            )
            x = HORIZONTAL_MARGIN + level * (
                120.0 + HORIZONTAL_GAP
            )
            for index, node in enumerate(nodes):
                width, height = _DIMENSIONS[node.kind]
                row_height = 80.0 + VERTICAL_GAP
                y = (
                    VERTICAL_MARGIN
                    + (widest - len(nodes)) * row_height / 2
                    + index * row_height
                    + (80.0 - height) / 2
                )
                bounds[node.element_id] = Bounds(
                    x=x + (level_width - width) / 2,
                    y=y,
                    width=width,
                    height=height,
                )

        positioned = tuple(
            PositionedFlow(flow, self._waypoints(bounds, flow))
            for flow in model.flows
        )
        return BpmnLayout(bounds=bounds, flows=positioned)

    @staticmethod
    def _levels(model: BpmnProcessModel) -> dict[str, int]:
        node_ids = {node.element_id for node in model.nodes}
        indegree = {node_id: 0 for node_id in node_ids}
        targets: dict[str, list[str]] = defaultdict(list)
        for flow in model.flows:
            indegree[flow.target_ref] += 1
            targets[flow.source_ref].append(flow.target_ref)

        ready = [node_id for node_id, degree in indegree.items() if degree == 0]
        heapq.heapify(ready)
        levels = {node_id: 0 for node_id in node_ids}
        visited = 0
        while ready:
            source = heapq.heappop(ready)
            visited += 1
            for target in sorted(targets[source]):
                levels[target] = max(levels[target], levels[source] + 1)
                indegree[target] -= 1
                if indegree[target] == 0:
                    heapq.heappush(ready, target)
        if visited != len(node_ids):
            raise UnsupportedBpmnGraphError(
                "ExecutionGraph cíclico não pode ser exportado para este layout."
            )
        return levels

    @staticmethod
    def _waypoints(
        bounds: dict[str, Bounds], flow: BpmnFlow
    ) -> tuple[tuple[float, float], ...]:
        source = bounds[flow.source_ref]
        target = bounds[flow.target_ref]
        start = (source.x + source.width, source.y + source.height / 2)
        end = (target.x, target.y + target.height / 2)
        if start[1] == end[1]:
            return (start, end)
        middle_x = (start[0] + end[0]) / 2
        return (
            start,
            (middle_x, start[1]),
            (middle_x, end[1]),
            end,
        )
