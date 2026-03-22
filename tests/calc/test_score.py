import dataclasses

import pytest
from strictacode.calc.score import (
    ImbalanceType,
    Metric,
    Status,
    _calculate_imbalance_multiplier,
    _calculate_imbalance_penalty,
    calculate,
)


class TestMetricStatus:
    @pytest.mark.parametrize("value, expected", [
        (0, Status.HEALTHY),
        (20, Status.HEALTHY),
        (21, Status.NORMAL),
        (40, Status.NORMAL),
        (41, Status.WARNING),
        (60, Status.WARNING),
        (61, Status.CRITICAL),
        (80, Status.CRITICAL),
        (81, Status.EMERGENCY),
        (100, Status.EMERGENCY),
    ])
    def test_status_boundaries(self, value, expected):
        m = Metric(value=value)
        assert m.status == expected

    def test_frozen(self):
        m = Metric(value=10)
        with pytest.raises(dataclasses.FrozenInstanceError):
            m.value = 20


class TestCalculateImbalancePenalty:
    def test_no_diff(self):
        penalty, itype = _calculate_imbalance_penalty(50, 50)
        assert penalty == 0
        assert itype is None

    def test_diff_at_boundary(self):
        penalty, itype = _calculate_imbalance_penalty(80, 50)
        assert penalty == 0
        assert itype is None

    def test_diff_just_over_boundary_spaghetti(self):
        penalty, itype = _calculate_imbalance_penalty(81, 50)
        assert penalty == 8
        assert itype is None

    def test_diff_40_spaghetti(self):
        penalty, itype = _calculate_imbalance_penalty(91, 50)
        assert penalty == 15
        assert itype == ImbalanceType.SPAGHETTI

    def test_diff_50_spaghetti(self):
        penalty, itype = _calculate_imbalance_penalty(101, 50)
        assert penalty == 25
        assert itype == ImbalanceType.SPAGHETTI

    def test_diff_just_over_boundary_overengineering(self):
        penalty, itype = _calculate_imbalance_penalty(50, 81)
        assert penalty == 3
        assert itype is None

    def test_diff_40_overengineering(self):
        penalty, itype = _calculate_imbalance_penalty(50, 91)
        assert penalty == 7
        assert itype == ImbalanceType.OVERENGINEERING

    def test_diff_50_overengineering(self):
        penalty, itype = _calculate_imbalance_penalty(50, 101)
        assert penalty == 12
        assert itype == ImbalanceType.OVERENGINEERING

    def test_asymmetry_spaghetti_punishes_more(self):
        penalty_sp, _ = _calculate_imbalance_penalty(101, 50)
        penalty_oe, _ = _calculate_imbalance_penalty(50, 101)
        assert penalty_sp > penalty_oe


class TestCalculateImbalanceMultiplier:
    def test_no_diff(self):
        mult, itype = _calculate_imbalance_multiplier(50, 50)
        assert mult == 1.0
        assert itype is None

    def test_boundary_30(self):
        mult, itype = _calculate_imbalance_multiplier(80, 50)
        assert mult == 1.0
        assert itype is None

    def test_just_over_boundary_spaghetti(self):
        mult, itype = _calculate_imbalance_multiplier(81, 50)
        assert mult == 1.25
        assert itype is None

    def test_diff_40_spaghetti(self):
        mult, itype = _calculate_imbalance_multiplier(91, 50)
        assert mult == 1.5
        assert itype == ImbalanceType.SPAGHETTI

    def test_diff_50_spaghetti(self):
        mult, itype = _calculate_imbalance_multiplier(101, 50)
        assert mult == 1.8
        assert itype == ImbalanceType.SPAGHETTI

    def test_just_over_boundary_overengineering(self):
        mult, itype = _calculate_imbalance_multiplier(50, 81)
        assert mult == 1.08
        assert itype is None

    def test_diff_40_overengineering(self):
        mult, itype = _calculate_imbalance_multiplier(50, 91)
        assert mult == 1.15
        assert itype == ImbalanceType.OVERENGINEERING

    def test_diff_50_overengineering(self):
        mult, itype = _calculate_imbalance_multiplier(50, 101)
        assert mult == 1.3
        assert itype == ImbalanceType.OVERENGINEERING


class TestCalculate:
    def test_without_imbalance(self):
        m = calculate(rp=10, oe=10, complexity_density=10.0, use_imbalance=False)
        assert m.value == 10
        assert m.penalty is None
        assert m.multiplier is None
        assert m.imbalance_type is None

    def test_without_imbalance_caps_at_100(self):
        m = calculate(rp=100, oe=100, complexity_density=100.0, use_imbalance=False)
        assert m.value == 100

    def test_additive_path_high_extremum(self):
        m = calculate(rp=80, oe=30, complexity_density=50.0)
        assert m.penalty is not None
        assert m.penalty > 0
        assert m.value == min(100, int(round(0.4 * 80 + 0.4 * 30 + 0.2 * 50)) + m.penalty)

    def test_additive_path_spaghetti_type(self):
        m = calculate(rp=91, oe=30, complexity_density=10.0)
        assert m.imbalance_type == ImbalanceType.SPAGHETTI

    def test_additive_path_overengineering_type(self):
        m = calculate(rp=30, oe=91, complexity_density=10.0)
        assert m.imbalance_type == ImbalanceType.OVERENGINEERING

    def test_multiplier_path_low_extremum(self):
        m = calculate(rp=34, oe=0, complexity_density=10.0)
        assert m.multiplier is not None
        assert m.multiplier > 1.0

    def test_multiplier_path_no_imbalance(self):
        m = calculate(rp=30, oe=5, complexity_density=10.0)
        assert m.multiplier == 1.0
        assert m.imbalance_type is None

    def test_density_converted_and_capped(self):
        """Density input 150 should be capped to 100 before weighting."""
        m = calculate(rp=0, oe=0, complexity_density=150.0, use_imbalance=False)
        assert m.value == 20  # 0.2 * 100 = 20

    def test_negative_input(self):
        m = calculate(rp=-10, oe=10, complexity_density=10.0, use_imbalance=False)
        assert m.value == 2  # int(round(0.4 * -10 + 0.4 * 10 + 0.2 * 10))

    def test_custom_weights(self):
        m = calculate(
            rp=50, oe=50, complexity_density=50.0,
            rp_weight=0.5, oe_weight=0.3, density_weight=0.2,
            use_imbalance=False,
        )
        assert m.value == 50  # 0.5*50 + 0.3*50 + 0.2*50

    def test_zero_inputs_with_imbalance(self):
        m = calculate(rp=0, oe=0, complexity_density=0.0, use_imbalance=True)
        assert m.value == 0
        assert m.status == Status.HEALTHY
