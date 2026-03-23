from dataclasses import dataclass


@dataclass(kw_only=True)
class ProjectStat:
    name: str
    score: int
    complexity_density: float
    refactoring_pressure: int
    overengineering_pressure: int


class ProjectDiff:
    def __init__(self, project_stat_one: ProjectStat, project_stat_two: ProjectStat):
        self._project_stat_one = project_stat_one
        self._project_stat_two = project_stat_two

    @property
    def stat_one(self) -> ProjectStat:
        return self._project_stat_one

    @property
    def stat_two(self) -> ProjectStat:
        return self._project_stat_two

    @property
    def score(self) -> int:
        return abs(self._project_stat_one.score - self._project_stat_two.score)

    @property
    def complexity_density(self) -> float:
        return round(abs(self._project_stat_one.complexity_density - self._project_stat_two.complexity_density), 2)

    @property
    def refactoring_pressure(self) -> int:
        return abs(self._project_stat_one.refactoring_pressure - self._project_stat_two.refactoring_pressure)

    @property
    def overengineering_pressure(self) -> int:
        return abs(self._project_stat_one.overengineering_pressure - self._project_stat_two.overengineering_pressure)
