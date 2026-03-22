from dataclasses import dataclass


@dataclass(kw_only=True)
class Threshold:
    score: int | None = None
    complexity_density: float | None = None
    refactoring_pressure: int | None = None
    overengineering_pressure: int | None = None

    @classmethod
    def from_string(cls, string) -> 'Threshold':
        try:
            return cls(score=int(string.strip()))
        except ValueError:
            pass

        score = None
        complexity_density = None
        refactoring_pressure = None
        overengineering_pressure = None

        thresholds = [i.strip() for i in string.split(',')]

        for threshold in thresholds:
            key, value = threshold.split('=', 1)

            if key.upper() == 'SCORE':
                score = int(value)
                continue
            if key.upper() == 'DENSITY':
                complexity_density = float(value)
                continue
            if key.upper() == 'RP':
                refactoring_pressure = int(value)
                continue
            if key.upper() == 'OP':
                overengineering_pressure = int(value)
                continue

            raise KeyError(f"Unrecognized threshold key: {key}")

        return cls(score=score,
                   refactoring_pressure=refactoring_pressure,
                   overengineering_pressure=overengineering_pressure,
                   complexity_density=complexity_density)

    def check(self, *,
              score: int,
              complexity_density: float,
              refactoring_pressure: int,
              overengineering_pressure: int) -> list[str]:
        errors = []

        if self.score is not None and score > self.score:
            errors.append(
                f"score exceeds threshold {score} > {self.score}",
            )
        if self.complexity_density is not None and complexity_density > self.complexity_density:
            errors.append(
                f"complexity density exceeds threshold {complexity_density} > {self.complexity_density}",
            )
        if self.refactoring_pressure is not None and refactoring_pressure > self.refactoring_pressure:
            errors.append(
                f"refactoring pressure exceeds threshold {refactoring_pressure} > {self.refactoring_pressure}",
            )
        if self.overengineering_pressure is not None and overengineering_pressure > self.overengineering_pressure:
            errors.append(
                f"overengineering pressure exceeds threshold "
                f"{overengineering_pressure} > {self.overengineering_pressure}",
            )

        return errors
