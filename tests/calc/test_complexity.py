import pytest

from strictacode.calc.complexity import Complexity, Status


class TestComplexityDensity:
    def test_normal_density(self):
        c = Complexity(score=50, loc=100)
        assert c.density == 50.0

    def test_small_density(self):
        c = Complexity(score=10, loc=1000)
        assert c.density == 1.0

    def test_zero_loc(self):
        c = Complexity(score=10, loc=0)
        assert c.density == 0.0

    def test_rounded_to_2_decimals(self):
        c = Complexity(score=1, loc=3)
        assert c.density == round((1 / 3) * 100, 2)


class TestComplexityStatus:
    @pytest.mark.parametrize("score, loc, expected", [
        (5, 100, Status.CLEAN),
        (10, 100, Status.CLEAN),       # boundary: density=10, not > 10
        (11, 100, Status.GOOD),
        (20, 100, Status.GOOD),        # boundary: density=20, not > 20
        (21, 100, Status.MODERATE),
        (30, 100, Status.MODERATE),    # boundary: density=30, not > 30
        (31, 100, Status.DIRTY),
        (50, 100, Status.DIRTY),       # boundary: density=50, not > 50
        (51, 100, Status.VERY_DIRTY),
        (75, 100, Status.VERY_DIRTY),  # boundary: density=75, not > 75
        (76, 100, Status.SPAGHETTI),
        (101, 100, Status.UNREADABLE),
    ])
    def test_status_boundaries(self, score, loc, expected):
        c = Complexity(score=score, loc=loc)
        assert c.status == expected


class TestComplexityTotal:
    def test_no_total_sum(self):
        child = Complexity(score=5, loc=10)
        c = Complexity(score=10, loc=100, children=[child])
        assert c.total == 10

    def test_total_sum(self):
        child = Complexity(score=5, loc=10)
        c = Complexity(score=10, loc=100, total_sum=True, children=[child])
        assert c.total == 15

    def test_total_sum_no_children(self):
        c = Complexity(score=10, loc=100, total_sum=True)
        assert c.total == 10

    def test_total_sum_multiple_children(self):
        c1 = Complexity(score=5, loc=10)
        c2 = Complexity(score=3, loc=8)
        c = Complexity(score=10, loc=100, total_sum=True, children=[c1, c2])
        assert c.total == 18


class TestComplexityStat:
    def test_no_children(self):
        c = Complexity(score=10, loc=100)
        assert c.stat.avg == 0
        assert c.stat.min == 0
        assert c.stat.max == 0
        assert c.stat.p50 == 0
        assert c.stat.p90 == 0

    def test_single_child(self):
        child = Complexity(score=10, loc=50)
        c = Complexity(score=5, loc=100, children=[child])
        assert c.stat.avg == 10
        assert c.stat.min == 10
        assert c.stat.max == 10
        assert c.stat.p50 == 10
        assert c.stat.p90 == 10

    def test_multiple_children(self):
        c1 = Complexity(score=10, loc=10)
        c2 = Complexity(score=20, loc=10)
        c3 = Complexity(score=30, loc=10)
        c4 = Complexity(score=40, loc=10)
        c5 = Complexity(score=50, loc=10)
        c = Complexity(score=0, loc=100, children=[c1, c2, c3, c4, c5])
        assert c.stat.avg == 30
        assert c.stat.min == 10
        assert c.stat.max == 50
        assert c.stat.p50 == 30
        assert c.stat.p90 == 46
