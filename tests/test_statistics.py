import pytest
from strictacode.statistics import ProjectDiff, ProjectStat

# ---------------------------------------------------------------------------
# ProjectStat
# ---------------------------------------------------------------------------


class TestProjectStat:
    def test_create_with_required_fields(self):
        stat = ProjectStat(
            name="test",
            score=10,
            complexity_density=5.5,
            refactoring_pressure=3,
            overengineering_pressure=2,
        )
        assert stat.name == "test"
        assert stat.score == 10
        assert stat.complexity_density == 5.5
        assert stat.refactoring_pressure == 3
        assert stat.overengineering_pressure == 2

    def test_defaults_not_required_with_kw_only(self):
        with pytest.raises(TypeError):
            ProjectStat("test", 10, 5.5, 3, 2)


# ---------------------------------------------------------------------------
# ProjectDiff
# ---------------------------------------------------------------------------


class TestProjectDiff:
    @pytest.fixture
    def stat_a(self):
        return ProjectStat(
            name="a",
            score=10,
            complexity_density=5.0,
            refactoring_pressure=8,
            overengineering_pressure=3,
        )

    @pytest.fixture
    def stat_b(self):
        return ProjectStat(
            name="b",
            score=20,
            complexity_density=7.5,
            refactoring_pressure=4,
            overengineering_pressure=7,
        )

    def test_score_diff_directional(self, stat_a, stat_b):
        diff = ProjectDiff(stat_a, stat_b)
        assert diff.score == -10

    def test_score_diff_reversed(self, stat_a, stat_b):
        diff = ProjectDiff(stat_b, stat_a)
        assert diff.score == 10

    def test_complexity_density_diff_directional(self, stat_a, stat_b):
        diff = ProjectDiff(stat_a, stat_b)
        assert diff.complexity_density == -2.5

    def test_complexity_density_rounded(self, stat_a, stat_b):
        stat_b_rated = ProjectStat(
            name="b",
            score=20,
            complexity_density=5.123,
            refactoring_pressure=4,
            overengineering_pressure=7,
        )
        diff = ProjectDiff(stat_a, stat_b_rated)
        assert diff.complexity_density == -0.12

    def test_refactoring_pressure_diff_directional(self, stat_a, stat_b):
        diff = ProjectDiff(stat_a, stat_b)
        assert diff.refactoring_pressure == 4

    def test_overengineering_pressure_diff_directional(self, stat_a, stat_b):
        diff = ProjectDiff(stat_a, stat_b)
        assert diff.overengineering_pressure == -4

    def test_stat_properties(self, stat_a, stat_b):
        diff = ProjectDiff(stat_a, stat_b)
        assert diff.stat_one is stat_a
        assert diff.stat_two is stat_b

    def test_zero_diff(self):
        stat = ProjectStat(
            name="same",
            score=10,
            complexity_density=5.0,
            refactoring_pressure=3,
            overengineering_pressure=2,
        )
        diff = ProjectDiff(stat, stat)
        assert diff.score == 0
        assert diff.complexity_density == 0.0
        assert diff.refactoring_pressure == 0
        assert diff.overengineering_pressure == 0
