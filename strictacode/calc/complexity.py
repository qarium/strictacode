import typing as t
from dataclasses import dataclass
from functools import cached_property

from numpy import percentile


@dataclass(kw_only=True)
class Stat:
    avg: int
    min: int
    max: int
    p50: int
    p90: int


class Complexity:
    def __init__(self, score: int, *,
                 loc: int,
                 total_sum: bool = False,
                 children: t.Optional[list['Complexity']] = None):
        self._score = score
        self._loc = loc

        self._total_sum = total_sum
        self._children = children or []

        self._stat: Stat = self._create_stat()

    @property
    def score(self) -> int:
        return self._score

    @property
    def loc(self) -> int:
        return self._loc

    @property
    def total(self) -> int:
        if self._total_sum:
            return self._score + sum((i.score for i in self._children))
        return self._score

    @cached_property
    def density(self) -> float:
        if self._loc > 0:
            return round((self._score / self._loc) * 100, 2)
        return 0.0

    @property
    def stat(self) -> Stat:
        return self._stat

    def _create_stat(self):
        scores = [i.score for i in self._children] or [0]

        try:
            avg = int(round(sum(scores) / len(self._children), 0))
        except ZeroDivisionError:
            avg = 0

        return Stat(avg=avg,
                    min=min(scores),
                    max=max(scores),
                    p90=int(round(percentile(scores, 90), 0)),
                    p50=int(round(percentile(scores, 50), 0)))
