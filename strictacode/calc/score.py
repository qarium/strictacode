import typing as t
from enum import Enum
from dataclasses import dataclass
from functools import cached_property

class ImbalanceType(str, Enum):
    SPAGHETTI = "spaghetti"
    OVERENGINEERING = "overengineering"


class Status(str, Enum):
    EMERGENCY = "emergency"
    CRITICAL = "critical"
    WARNING = "warning"
    NORMAL = "normal"
    HEALTHY = "healthy"


@dataclass(kw_only=True, frozen=True)
class Metric:
    value: int
    penalty: t.Optional[int] = None
    multiplier: t.Optional[float] = None
    imbalance_type: t.Optional[ImbalanceType] = None

    @cached_property
    def status(self) -> Status:
        if self.value > 80:
            return Status.EMERGENCY
        if self.value > 60:
            return Status.CRITICAL
        if self.value > 40:
            return Status.WARNING
        if self.value > 20:
            return Status.NORMAL

        return Status.HEALTHY


def _calculate_imbalance_penalty(rp: int, oe: int) -> tuple[int, t.Optional[ImbalanceType]]:
    """
    Рассчитывает штраф за перекос между RP и OE.
    Возвращает (penalty, imbalance_type) или (0, None) если перекоса нет.

    Spaghetti (RP >> OE) наказывается сильнее — острая проблема.
    Overengineering (OE >> RP) наказывается мягче — хроническая проблема.
    """
    diff = abs(rp - oe)

    if diff <= 30:
        return 0, None

    if rp > oe:  # Spaghetti — острая боль
        if diff > 50:
            return 25, ImbalanceType.SPAGHETTI
        if diff > 40:
            return 15, ImbalanceType.SPAGHETTI

        return 8, None

    # Overengineering — хроническая боль
    if diff > 50:
        return 12, ImbalanceType.OVERENGINEERING
    if diff > 40:
        return 7, ImbalanceType.OVERENGINEERING

    return 3, None


def _calculate_imbalance_multiplier(rp: int, oe: int) -> tuple[float, t.Optional[ImbalanceType]]:
    """
    Рассчитывает множитель за перекос между RP и OE (для низкого экстремума).
    Возвращает (multiplier, imbalance_type) или (1.0, None) если перекоса нет.
    """
    diff = abs(rp - oe)

    if diff <= 30:
        return 1.0, None

    if rp > oe:  # Spaghetti
        if diff > 50:
            return 1.8, ImbalanceType.SPAGHETTI
        if diff > 40:
            return 1.5, ImbalanceType.SPAGHETTI

        return 1.25, None

    # Overengineering
    if diff > 50:
        return 1.3, ImbalanceType.OVERENGINEERING
    if diff > 40:
        return 1.15, ImbalanceType.OVERENGINEERING

    return 1.08, None


def calculate(rp: int, oe: int, complexity_density: float) -> Metric:
    density = min(100, int(complexity_density))
    extremum = max(rp, oe)

    base_score = int(round(0.4 * rp + 0.4 * oe + 0.2 * density, 0))

    # Гибридный подход:
    # аддитив для высокого экстремума
    if extremum >= 35:
        penalty, imbalance_type = _calculate_imbalance_penalty(rp, oe)
        score = min(100, base_score + penalty)
        return Metric(
            value=score,
            penalty=penalty,
            imbalance_type=imbalance_type,
        )

    # множитель для низкого
    multiplier, imbalance_type = _calculate_imbalance_multiplier(rp, oe)
    score = min(100, int(base_score * multiplier))
    return Metric(
        value=score,
        multiplier=multiplier,
        imbalance_type=imbalance_type,
    )
