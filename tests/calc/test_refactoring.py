import math

import pytest

from strictacode.calc.pressure.refactoring import (
    Data,
    Metric,
    Status,
    _base_pressure,
    _density_scale,
    _peak_pressure,
    _peak_scale,
    calculate,
)


class TestMetricStatus:
    @pytest.mark.parametrize("value, expected", [
        (0, Status.MINIMAL),
        (20, Status.MINIMAL),
        (21, Status.LOW),
        (40, Status.LOW),
        (41, Status.MEDIUM),
        (60, Status.MEDIUM),
        (61, Status.HIGH),
        (80, Status.HIGH),
        (81, Status.EXTREME),
    ])
    def test_status_boundaries(self, value, expected):
        data = Data(loc=100, max_complexity=1, p90_complexity=1, complexity_density=1.0)
        m = Metric(score=value, data=data)
        assert m.status == expected


class TestPeakScale:
    @pytest.mark.parametrize("loc, expected", [
        (0, 0.25),
        (1, 0.25),
        (999, 0.25),
        (1000, 0.5),
        (5000, 0.5),
        (9999, 0.5),
        (10000, 0.75),
        (50000, 0.75),
        (99999, 0.75),
        (100000, 1.0),
    ])
    def test_peak_scale(self, loc, expected):
        assert _peak_scale(loc) == expected


class TestDensityScale:
    @pytest.mark.parametrize("loc, expected", [
        (0, 0.5),
        (1, 0.5),
        (499, 0.5),
        (500, 1.0),
        (1000, 1.0),
        (4999, 1.0),
        (5000, 2.0),
        (10000, 2.0),
        (19999, 2.0),
        (20000, 3.0),
    ])
    def test_density_scale(self, loc, expected):
        assert _density_scale(loc) == expected


class TestPeakPressure:
    def test_zero_complexity(self):
        result = _peak_pressure(0, 0, 5000)
        assert result == 0

    def test_known_values(self):
        # combined = 10*0.6 + 5*0.4 = 8.0
        # raw_peak = 100 * (1 - exp(-0.08*8)) = 100 * (1 - exp(-0.64))
        expected_raw = 100 * (1 - math.exp(-0.08 * 8.0))
        scale = _peak_scale(5000)  # 0.75
        expected = int(expected_raw * scale)
        assert _peak_pressure(10, 5, 5000) == expected

    def test_high_complexity(self):
        result = _peak_pressure(50, 40, 5000)
        assert result > _peak_pressure(10, 5, 5000)

    def test_loc_scale_increases_result(self):
        small = _peak_pressure(20, 10, 500)
        large = _peak_pressure(20, 10, 50000)
        assert large > small

    def test_max_heavily_weighted_over_p90(self):
        result = _peak_pressure(100, 1, 10000)
        assert result > 50


class TestBasePressure:
    def test_zero_density(self):
        result = _base_pressure(0.0, 5000)
        assert result == 0

    def test_known_values(self):
        # scale for loc=5000 is 2.0, adjusted = 5.0 * 2.0 = 10.0
        expected = int(100 * (1 - math.exp(-0.02 * 10.0)))
        assert _base_pressure(5.0, 5000) == expected

    def test_high_density(self):
        result = _base_pressure(50.0, 20000)
        assert result > 80

    def test_loc_scale_increases_result(self):
        small = _base_pressure(10.0, 500)
        large = _base_pressure(10.0, 20000)
        assert large > small


class TestCalculate:
    def test_basic(self):
        data = Data(loc=1000, max_complexity=10, p90_complexity=5, complexity_density=5.0)
        m = calculate(data)
        assert isinstance(m, Metric)
        assert 0 <= m.score <= 100

    def test_data_stored(self):
        data = Data(loc=1000, max_complexity=10, p90_complexity=5, complexity_density=5.0)
        m = calculate(data)
        assert m.data.loc == 1000
        assert m.data.max_complexity == 10
        assert m.data.p90_complexity == 5

    def test_custom_weights_peak_only(self):
        data = Data(loc=1000, max_complexity=10, p90_complexity=5, complexity_density=5.0)
        m_custom = calculate(data, w_peak=1.0, w_base=0.0)
        # С w_base=0.0 результат должен быть равен только peak pressure
        expected_peak = _peak_pressure(data.max_complexity, data.p90_complexity, data.loc)
        assert m_custom.score == expected_peak

    def test_custom_weights_base_only(self):
        data = Data(loc=1000, max_complexity=10, p90_complexity=5, complexity_density=5.0)
        m_custom = calculate(data, w_peak=0.0, w_base=1.0)
        expected_base = _base_pressure(data.complexity_density, data.loc)
        assert m_custom.score == expected_base

    def test_stat_empty_children(self):
        data = Data(loc=1000, max_complexity=1, p90_complexity=1, complexity_density=1.0)
        m = calculate(data, children=[])
        assert m.stat.avg == 0
        assert m.stat.min == 0
        assert m.stat.max == 0
        assert m.stat.p50 == 0
        assert m.stat.p90 == 0

    def test_children_stat_multiple_children(self):
        data = Data(loc=1000, max_complexity=10, p90_complexity=5, complexity_density=5.0)
        children = [
            Metric(score=10, data=Data(loc=100, max_complexity=1, p90_complexity=1, complexity_density=1.0)),
            Metric(score=20, data=Data(loc=100, max_complexity=1, p90_complexity=1, complexity_density=1.0)),
            Metric(score=30, data=Data(loc=100, max_complexity=1, p90_complexity=1, complexity_density=1.0)),
        ]
        m = calculate(data, children=children)
        assert m.stat.avg == 20
        assert m.stat.min == 10
        assert m.stat.max == 30
        assert m.stat.p50 == 20
        assert m.stat.p90 == 28

    def test_caps_at_100(self):
        data = Data(loc=100000, max_complexity=100, p90_complexity=80, complexity_density=100.0)
        m = calculate(data)
        assert m.score <= 100
