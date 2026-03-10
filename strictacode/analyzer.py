from .source import Sources


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


class Analyzer:
    def __init__(self, sources: Sources):
        self._sources = sources

    def analyze_sources(self):
        statuses = {
            "rp": refactoring_pressure_status(self._sources.refactoring_pressure.score),
            "cd": complexity_density_status(self._sources.complexity.density),
        }

        rp = self._sources.refactoring_pressure.score
        normalized_density = min(100, int(self._sources.complexity.density))

        self._sources.status.score = int(round(0.7 * rp + 0.3 * normalized_density, 0))
        self._sources.status.name = project_status(self._sources.status.score)

        reasons = {
            "rp": {
                ("high", "extreme"): "Excessive refactoring pressure",
                ("medium", ): "Increased refactoring pressure",
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
