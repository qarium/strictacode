from .calc import complexity, score
from .calc.pressure import overengineering, refactoring
from .source import Sources


class Analyzer:
    def __init__(self, sources: Sources):
        self._sources = sources

    def analyze_sources(self):
        statuses = {
            "density": self._sources.complexity.status,
            "refactoring": self._sources.refactoring_pressure.status,
            "overengineering": self._sources.overengineering_pressure.status,
        }
        reasons = {
            "density": {
                (complexity.Status.SPAGHETTI,
                 complexity.Status.UNREADABLE): "Excessively high concentration of complexity",
                (complexity.Status.DIRTY,
                 complexity.Status.VERY_DIRTY): "High concentration of complexity",
                (complexity.Status.MODERATE,): "The concentration of complexity requires attention",
            },
            "refactoring": {
                (refactoring.Status.HIGH,
                 refactoring.Status.EXTREME): "Excessive refactoring pressure",
                (refactoring.Status.MEDIUM,): "Increased refactoring pressure",
            },
            "overengineering": {
                (overengineering.Status.BLOATED,
                 overengineering.Status.OVERENGINEERED): "Excessive abstraction depth (Overengineering)",
                (overengineering.Status.COMPLEX,): "Approaching complexity threshold",
            },
        }
        imbalance_reasons = {
            score.ImbalanceType.SPAGHETTI: "High RP/OE imbalance - possibly spaghetti code",
            score.ImbalanceType.OVERENGINEERING: "High OE/RP imbalance - possibly overengineering",
        }

        if self._sources.status.score.imbalance_type:
            self._sources.status.reasons.append(
                imbalance_reasons[self._sources.status.score.imbalance_type],
            )

        if self._sources.status.name != score.Status.HEALTHY:
            for s_type, s_name in statuses.items():
                if status_reasons := [v for k, v in reasons[s_type].items() if s_name in k]:
                    self._sources.status.reasons.extend(status_reasons)

    def analyze(self):
        self.analyze_sources()
