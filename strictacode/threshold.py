import typing as t
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class Threshold:
    score: t.Optional[int] = None
    refactoring_pressure: t.Optional[int] = None
    overengineering_pressure: t.Optional[int] = None
    complexity_density: t.Optional[float] = None

    @classmethod
    def from_string(cls, string) -> 'Threshold':
        try:
            return cls(score=int(string.strip()))
        except ValueError:
            pass

        score = None
        refactoring_pressure = None
        overengineering_pressure = None
        complexity_density = None

        thresholds = [i.strip() for i in string.split(',')]

        for threshold in thresholds:
            key, value = threshold.split('=', 1)

            if key.upper() == 'SCORE':
                score = int(value)
            elif key.upper() == 'RP':
                refactoring_pressure = int(value)
            elif key.upper() == 'OP':
                overengineering_pressure = int(value)
            elif key.upper() == 'DENSITY':
                complexity_density = float(value)

        return cls(score=score,
                   refactoring_pressure=refactoring_pressure,
                   overengineering_pressure=overengineering_pressure,
                   complexity_density=complexity_density)

    def check(self, *,
              score: int,
              refactoring_pressure: int,
              overengineering_pressure: int,
              complexity_density: float) -> list[str]:
        errors = []

        if self.score is not None and score > self.score:
            errors.append(
                f'Score exceeds threshold: current={score} threshold={self.score}',
            )
        if self.refactoring_pressure is not None and refactoring_pressure > self.refactoring_pressure:
            errors.append(
                f'Refactoring pressure exceeds threshold: '
                f'current={refactoring_pressure} threshold={self.refactoring_pressure}',
            )
        if self.overengineering_pressure is not None and overengineering_pressure > self.overengineering_pressure:
            errors.append(
                f'Overengineering pressure exceeds threshold: '
                f'current={overengineering_pressure} threshold={self.overengineering_pressure}',
            )
        if self.complexity_density is not None and complexity_density > self.complexity_density:
            errors.append(
                f'Complexity density exceeds threshold: '
                f'current={complexity_density} threshold={self.complexity_density}',
            )

        return errors
