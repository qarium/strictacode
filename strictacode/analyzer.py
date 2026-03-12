import typing as t

from .source import Sources


def calculate_imbalance_penalty(rp: int, oe: int) -> tuple[int, t.Optional[str]]:
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
            return 25, "spaghetti"
        if diff > 40:
            return 15, "spaghetti"
        return 8, "spaghetti"

    # Overengineering — хроническая боль
    if diff > 50:
        return 12, "overengineering"
    if diff > 40:
        return 7, "overengineering"
    return 3, "overengineering"


def calculate_imbalance_multiplier(rp: int, oe: int) -> tuple[float, t.Optional[str]]:
    """
    Рассчитывает множитель за перекос между RP и OE (для низкого экстремума).
    Возвращает (multiplier, imbalance_type) или (1.0, None) если перекоса нет.
    """
    diff = abs(rp - oe)

    if diff <= 30:
        return 1.0, None

    if rp > oe:  # Spaghetti
        if diff > 50:
            return 1.8, "spaghetti"
        if diff > 40:
            return 1.5, "spaghetti"
        return 1.25, "spaghetti"

    # Overengineering
    if diff > 50:
        return 1.3, "overengineering"
    if diff > 40:
        return 1.15, "overengineering"
    return 1.08, "overengineering"


def overengineering_pressure_status(score: int):
    if score > 80:
        return "bloated"
    if score > 60:
        return "overengineered"
    if score > 40:
        return "complex"
    if score > 20:
        return "moderate"
    return "simple"


def refactoring_pressure_status(score: int):
    if score > 80:
        return "extreme"
    if score > 60:
        return "high"
    if score > 40:
        return "medium"
    if score > 20:
        return "low"
    return "minimal"


def complexity_density_status(score: float):
    if score > 100:
        return "unreadable"
    if score > 75:
        return "spaghetti"
    if score > 50:
        return "very-dirty"
    if score > 30:
        return "dirty"
    if score > 20:
        return "moderate"
    if score > 10:
        return "good"
    return "clean"


def project_status(score: int):
    if score > 80:
        return "emergency"
    if score > 60:
        return "critical"
    if score > 40:
        return "warning"
    if score > 20:
        return "normal"
    return "healthy"


def calculate_project_score(rp: int, oe: int, complexity_density: float) -> tuple[int, t.Optional[str]]:
    density = min(100, int(complexity_density))
    extremum = max(rp, oe)

    base_score = int(round(0.4 * rp + 0.4 * oe + 0.2 * density, 0))

    # Гибридный подход:
    # аддитив для высокого экстремума
    if extremum >= 35:
        penalty, imbalance_type = calculate_imbalance_penalty(rp, oe)
        return min(100, base_score + penalty), imbalance_type

    # множитель для низкого
    multiplier, imbalance_type = calculate_imbalance_multiplier(rp, oe)
    return min(100, int(base_score * multiplier)), imbalance_type


class Analyzer:
    def __init__(self, sources: Sources):
        self._sources = sources

    def analyze_sources(self):
        statuses = {
            "oe": overengineering_pressure_status(self._sources.overengineering_pressure.score),
            "rp": refactoring_pressure_status(self._sources.refactoring_pressure.score),
            "cd": complexity_density_status(self._sources.complexity.density),
        }

        rp = self._sources.refactoring_pressure.score
        op = self._sources.overengineering_pressure.score
        density = self._sources.complexity.density

        self._sources.status.score, imbalance_type = calculate_project_score(rp, op, density)
        self._sources.status.name = project_status(self._sources.status.score)

        # Добавить reason для перекоса
        if imbalance_type:
            imbalance_reasons = {
                "spaghetti": "High RP/OE imbalance - spaghetti code pattern",
                "overengineering": "High OE/RP imbalance - overengineering pattern",
            }
            self._sources.status.reasons.append(imbalance_reasons[imbalance_type])

        reasons = {
            "rp": {
                ("high", "extreme"): "Excessive refactoring pressure",
                ("medium", ): "Increased refactoring pressure",
            },
            "oe": {
                ("bloated", "overengineered"): "Excessive abstraction depth (Overengineering)",
                ("complex", ): "Approaching complexity threshold",
            },
            "cd": {
                ("spaghetti", "unreadable"): "Excessively high concentration of complexity",
                ("dirty", "very-dirty"): "High concentration of complexity",
                ("moderate", ): "The concentration of complexity requires attention",
            },
        }

        if self._sources.status.name != "healthy":
            for s_type, s_name in statuses.items():
                if status_reasons := [v for k, v in reasons[s_type].items() if s_name in k]:
                    self._sources.status.reasons.append(next(iter(status_reasons)))

    def analyze(self):
        self.analyze_sources()
