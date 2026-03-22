import pytest

from strictacode.threshold import Threshold


class TestThresholdDefaults:
    def test_all_defaults_are_none(self):
        t = Threshold()
        assert t.score is None
        assert t.complexity_density is None
        assert t.refactoring_pressure is None
        assert t.overengineering_pressure is None


class TestThresholdFromString:
    def test_plain_int_sets_score(self):
        t = Threshold.from_string("50")
        assert t.score == 50
        assert t.complexity_density is None
        assert t.refactoring_pressure is None
        assert t.overengineering_pressure is None

    @pytest.mark.parametrize("input_str, field, value", [
        ("SCORE=50", "score", 50),
        ("score=50", "score", 50),
        ("DENSITY=30.5", "complexity_density", 30.5),
        ("RP=60", "refactoring_pressure", 60),
        ("OP=70", "overengineering_pressure", 70),
    ])
    def test_single_key_parses_correctly(self, input_str, field, value):
        t = Threshold.from_string(input_str)
        assert getattr(t, field) == value

    def test_multiple_keys(self):
        t = Threshold.from_string("SCORE=50,RP=60")
        assert t.score == 50
        assert t.refactoring_pressure == 60

    def test_whitespace_handling_plain_int(self):
        t = Threshold.from_string("  50  ")
        assert t.score == 50

    def test_unknown_key_raises_key_error(self):
        with pytest.raises(KeyError, match="Unrecognized threshold key: FOO"):
            Threshold.from_string("FOO=10")

    def test_empty_string_raises_value_error(self):
        # Empty string fails: int("") raises ValueError, then "".split(',') gives [""],
        # and "".split('=', 1) produces [""] which fails to unpack.
        with pytest.raises(ValueError):
            Threshold.from_string("")

    def test_non_numeric_value_raises_value_error(self):
        with pytest.raises(ValueError):
            Threshold.from_string("SCORE=abc")

    def test_empty_value_after_equals_raises_value_error(self):
        with pytest.raises(ValueError):
            Threshold.from_string("SCORE=")

    def test_from_string_with_zero_threshold(self):
        t = Threshold.from_string("SCORE=0")
        assert t.score == 0
        assert t.complexity_density is None
        assert t.refactoring_pressure is None
        assert t.overengineering_pressure is None

    def test_from_string_trailing_comma(self):
        with pytest.raises(ValueError):
            Threshold.from_string("SCORE=50,")


class TestThresholdCheck:
    def test_no_thresholds_set_returns_empty_errors(self):
        t = Threshold()
        errors = t.check(
            score=100,
            complexity_density=50.0,
            refactoring_pressure=80,
            overengineering_pressure=90,
        )
        assert errors == []

    def test_score_exceeds_threshold(self):
        t = Threshold(score=50)
        errors = t.check(
            score=60,
            complexity_density=0.0,
            refactoring_pressure=0,
            overengineering_pressure=0,
        )
        assert len(errors) == 1
        assert "score exceeds threshold 60 > 50" in errors[0]

    def test_score_within_threshold(self):
        t = Threshold(score=50)
        errors = t.check(
            score=40,
            complexity_density=0.0,
            refactoring_pressure=0,
            overengineering_pressure=0,
        )
        assert errors == []

    def test_score_equal_to_threshold_no_error(self):
        t = Threshold(score=50)
        errors = t.check(
            score=50,
            complexity_density=0.0,
            refactoring_pressure=0,
            overengineering_pressure=0,
        )
        assert errors == []

    def test_complexity_density_exceeds_threshold(self):
        t = Threshold(complexity_density=10.0)
        errors = t.check(
            score=0,
            complexity_density=15.5,
            refactoring_pressure=0,
            overengineering_pressure=0,
        )
        assert len(errors) == 1
        assert "complexity density exceeds threshold 15.5 > 10.0" in errors[0]

    def test_refactoring_pressure_exceeds_threshold(self):
        t = Threshold(refactoring_pressure=40)
        errors = t.check(
            score=0,
            complexity_density=0.0,
            refactoring_pressure=50,
            overengineering_pressure=0,
        )
        assert len(errors) == 1
        assert "refactoring pressure exceeds threshold 50 > 40" in errors[0]

    def test_overengineering_pressure_exceeds_threshold(self):
        t = Threshold(overengineering_pressure=30)
        errors = t.check(
            score=0,
            complexity_density=0.0,
            refactoring_pressure=0,
            overengineering_pressure=45,
        )
        assert len(errors) == 1
        assert "overengineering pressure exceeds threshold 45 > 30" in errors[0]

    def test_multiple_exceeded_returns_multiple_errors(self):
        t = Threshold(score=10, complexity_density=5.0, refactoring_pressure=10, overengineering_pressure=10)
        errors = t.check(
            score=20,
            complexity_density=10.0,
            refactoring_pressure=30,
            overengineering_pressure=0,
        )
        assert len(errors) == 3
        assert any("score exceeds threshold" in e for e in errors)
        assert any("complexity density exceeds threshold" in e for e in errors)
        assert any("refactoring pressure exceeds threshold" in e for e in errors)
