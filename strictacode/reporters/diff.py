import abc
import json

from .. import utils
from ..statistics import ProjectDiff


class BaseDiffReporter(metaclass=abc.ABCMeta):
    def __init__(self, project_diff: ProjectDiff, *, details: bool = False, output: str | None = None):
        self._project_diff = project_diff

        self._output = output
        self._details = details

    @abc.abstractmethod
    def _report(self) -> None:
        pass

    def report(self) -> None:
        if self._output is not None:
            with utils.redirect_output(self._output):
                return self._report()
        return self._report()


class TextDiffReporter(BaseDiffReporter):
    def _report_diff(self):
        print("Diff:")
        print(f"  * score: {self._project_diff.score}")
        print(f"  * complexity_density: {self._project_diff.complexity_density}")
        print(f"  * refactoring_pressure: {self._project_diff.refactoring_pressure}")
        print(f"  * overengineering_pressure: {self._project_diff.overengineering_pressure}")

    def _report_results(self):
        print()
        print("---")
        print()
        print(f"{self._project_diff.stat_one.name.title()}:")
        print(f"  * score: {self._project_diff.stat_one.score}")
        print(f"  * complexity_density: {self._project_diff.stat_one.complexity_density}")
        print(f"  * refactoring_pressure: {self._project_diff.stat_one.refactoring_pressure}")
        print(f"  * overengineering_pressure: {self._project_diff.stat_one.overengineering_pressure}")
        print()
        print("---")
        print()
        print(f"{self._project_diff.stat_two.name.title()}:")
        print(f"  * score: {self._project_diff.stat_two.score}")
        print(f"  * complexity_density: {self._project_diff.stat_two.complexity_density}")
        print(f"  * refactoring_pressure: {self._project_diff.stat_two.refactoring_pressure}")
        print(f"  * overengineering_pressure: {self._project_diff.stat_two.overengineering_pressure}")

    def _report(self) -> None:
        self._report_diff()

        if self._details:
            self._report_results()


class JsonDiffReporter(BaseDiffReporter):
    def _report_results(self, data: dict) -> None:
        data[self._project_diff.stat_one.name] = {
            "score": self._project_diff.stat_one.score,
            "complexity_density": self._project_diff.stat_one.complexity_density,
            "refactoring_pressure": self._project_diff.stat_one.refactoring_pressure,
            "overengineering_pressure": self._project_diff.stat_one.overengineering_pressure,
        }
        data[self._project_diff.stat_two.name] = {
            "score": self._project_diff.stat_two.score,
            "complexity_density": self._project_diff.stat_two.complexity_density,
            "refactoring_pressure": self._project_diff.stat_two.refactoring_pressure,
            "overengineering_pressure": self._project_diff.stat_two.overengineering_pressure,
        }

    def _report(self) -> None:
        data = {
            "diff": {
                "score": self._project_diff.score,
                "complexity_density": self._project_diff.complexity_density,
                "refactoring_pressure": self._project_diff.refactoring_pressure,
                "overengineering_pressure": self._project_diff.overengineering_pressure,
            },
        }

        if self._details:
            self._report_results(data)

        print(json.dumps(data, indent=2))
