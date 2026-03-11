import math
import typing as t
from numpy import percentile
from dataclasses import dataclass

W_PEAK: t.Final[float] = 0.6
W_BASE: t.Final[float] = 0.4


@dataclass(kw_only=True)
class Data:
    loc: int
    max_complexity: int
    p90_complexity: int
    complexity_density: float


@dataclass(kw_only=True)
class Stat:
    avg: int = 0
    max: int = 0
    min: int = 0
    p90: int = 0
    p50: int = 0


class Metric:
    def __init__(self, score: int, data: Data, *,
                 children: t.Optional[list['Metric']] = None):
        self._score = score
        self._data = data

        self._children = children or []

        self._stat: Stat = self._create_stat()

    @property
    def score(self) -> int:
        return self._score

    @property
    def data(self) -> Data:
        return self._data

    @property
    def stat(self) -> Stat:
        return self._stat

    def _create_stat(self) -> Stat:
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


def _peak_scale(loc: int) -> float:
    """
    Scale factor для peak_pressure.

    Логика: на маленьких проектах один плохой файл — не системная проблема.
    Чем больше проект, тем значимее пиковые значения.
    """
    if loc < 1000:
        return 0.25
    if loc < 10000:
        return 0.5
    if loc < 100000:
        return 0.75
    return 1.0


def _density_scale(loc: int) -> float:
    """
    Scale factor для density.

    Логика: density = complexity / loc.
    На больших проектах density естественным образом ниже.
    Scale компенсирует это.
    """
    if loc < 500:
        return 0.5
    if loc < 5000:
        return 1.0
    if loc < 20000:
        return 2.0
    return 3.0


def _peak_pressure(max_complexity: int, p90_complexity: int, loc: int) -> int:
    """
    Пиковое давление от самых сложных функций.

    Аргументы:
        max_complexity: Максимальная сложность
        p90_complexity: 90-й перцентиль сложности
        loc: Количество строк кода (для масштабирования)

    Нелинейная шкала (экспонента):
    - complexity 10 → ~40%
    - complexity 15 → ~60%
    - complexity 25 → ~85%
    - complexity 40 → ~95%

    Масштабируется по loc: на малых проектах пики менее значимы.
    """
    combined = max_complexity * 0.6 + p90_complexity * 0.4
    raw_peak = 100 * (1 - math.exp(-0.08 * combined))
    scale = _peak_scale(loc)
    return int(raw_peak * scale)


def _base_pressure(complexity_density: float, loc: int) -> int:
    """
    Базовое давление от качества кода.

    Аргументы:
        complexity_density: (total_complexity / loc) * 100
        loc: Количество строк кода (для масштабирования)
    """
    scale = _density_scale(loc)
    adjusted_density = complexity_density * scale
    return int(100 * (1 - math.exp(-0.02 * adjusted_density)))


def calculate(data: Data, *,
              w_peak: float = W_PEAK,
              w_base: float = W_BASE,
              children: t.Optional[list[Metric]] = None) -> Metric:
    """
    Refactoring Pressure — давление на рефакторинг.

    RP = w_peak * Peak(max, p90, loc) + w_base * Base(density, loc)

    Аргументы:
        max_complexity: Максимальная сложность
        p90_complexity: 90-й перцентиль сложности
        complexity_density: (total_complexity / loc) * 100
        loc: Количество строк кода
        w_peak: Вес пикового давления (по умолчанию 0.6)
        w_base: Вес базового давления (по умолчанию 0.4)

    Возвращает:
        int: RP в диапазоне [0, 100]

    Шкала RP:
        - 0-20:  Код здоров
        - 20-40: Лёгкое давление
        - 40-60: Заметное давление
        - 60-80: Сильное давление
        - 80-100: Критическое состояние
    """
    peak = _peak_pressure(data.max_complexity, data.p90_complexity, data.loc)
    base = _base_pressure(data.complexity_density, data.loc)

    value = w_peak * peak + w_base * base
    score = int(round(min(100, int(value))))

    return Metric(score, data, children=children)
