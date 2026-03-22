"""
Overengineering pressure.
"""

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from functools import cached_property

from numpy import percentile

from ...graph import DiGraph


@dataclass(kw_only=True)
class Score:
    path: str
    name: str
    value: float


@dataclass(kw_only=True)
class Stat:
    avg: int = 0
    max: int = 0
    min: int = 0
    p90: int = 0
    p50: int = 0


@dataclass(kw_only=True)
class CalcResult:
    score: float | int
    classes: list[Score]
    modules: list[Score]

    def __post_init__(self):
        self.score = int(round(self.score, 0))


class Status(str, Enum):
    BLOATED = "bloated"
    OVERENGINEERED = "overengineered"
    COMPLEX = "complex"
    MODERATE = "moderate"
    SIMPLE = "simple"


class Metric:
    def __init__(self, score: int, *, children: list["Metric"] | None = None):
        self._score = score
        self._children = children or []

        self._stat: Stat = self._create_stat()

    @property
    def score(self) -> int:
        return self._score

    @property
    def stat(self) -> Stat:
        return self._stat

    @cached_property
    def status(self) -> Status:
        if self._score > 80:
            return Status.BLOATED
        if self._score > 60:
            return Status.OVERENGINEERED
        if self._score > 40:
            return Status.COMPLEX
        if self._score > 20:
            return Status.MODERATE

        return Status.SIMPLE

    def _create_stat(self):
        scores = [i.score for i in self._children] or [0]
        return Stat(
            avg=int(round(sum(scores) / len(scores), 0)),
            max=int(round(max(scores), 0)),
            min=int(round(min(scores), 0)),
            p50=int(round(percentile(scores, 50), 0)),
            p90=int(round(percentile(scores, 90), 0)),
        )


def _fan_out(graph):
    return {n: len(graph.neighbors(n)) for n in graph.nodes}


def _fan_in(graph):
    r = graph.reverse()
    return {n: len(r.neighbors(n)) for n in graph.nodes}


def _shortest_paths(graph, start):
    dist = {start: 0}
    q = deque([start])

    while q:
        v = q.popleft()

        for n in graph.neighbors(v):
            if n not in dist:
                dist[n] = dist[v] + 1
                q.append(n)

    return dist


def _depth_scores(graph):
    depth = {}

    for n in graph.nodes:
        d = _shortest_paths(graph, n)
        depth[n] = max(d.values()) if d else 0

    return depth


def _centrality(graph: DiGraph):
    score = defaultdict(int)

    for start in graph.nodes:
        visited = set()
        q = deque([start])

        while q:
            v = q.popleft()

            for n in graph.neighbors(v):
                if n not in visited:
                    visited.add(n)
                    score[n] += 1
                    q.append(n)

    return score


def _norm(v, t):
    return min(1.0, v / t)


def _class_scores(graph: DiGraph) -> list[Score]:
    fout = _fan_out(graph)
    fin = _fan_in(graph)
    depth = _depth_scores(graph)
    cent = _centrality(graph)

    scores = []

    for node in graph.nodes:
        score = (
            0.35 * _norm(fout[node], 7)
            + 0.25 * _norm(fin[node], 10)
            + 0.25 * _norm(depth[node], 8)
            + 0.15 * _norm(cent[node], 20)
        ) * 100

        if ":" not in node:
            continue

        filepath, cls_name = node.split(":", 1)

        scores.append(
            Score(name=cls_name, path=filepath, value=round(score, 2)),
        )

    return scores


def _module_scores(cls_scores: list[Score]) -> list[Score]:
    modules = defaultdict(list)

    for score in cls_scores:
        modules[score.path].append(score.value)

    result = []

    for path, values in modules.items():
        values = sorted(values, reverse=True)
        result.append(Score(path=path, name=os.path.basename(path), value=sum(values) / len(values)))

    return result


def _common_score(graph: DiGraph, cls_scores: list[Score]) -> float:
    coupling = graph.number_of_edges() / max(graph.number_of_nodes(), 1)
    avg_class = sum(i.value for i in cls_scores) / max(len(cls_scores), 1)

    score = (0.4 * _norm(coupling, 4) + 0.6 * _norm(avg_class, 70)) * 100

    return round(score, 2)


def calculate(graph: DiGraph) -> CalcResult:
    cls_scores = _class_scores(graph)
    mod_scores = _module_scores(cls_scores)
    proj_score = _common_score(graph, cls_scores)

    return CalcResult(score=proj_score, classes=cls_scores, modules=mod_scores)
