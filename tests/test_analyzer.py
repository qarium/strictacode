import pytest

from strictacode.analyzer import Analyzer
from strictacode.calc import score, complexity
from strictacode.calc.pressure import refactoring
from strictacode.calc.pressure import overengineering
from strictacode.source import Sources


def _make_sources(
    *,
    score_value=10,
    score_status=score.Status.HEALTHY,
    imbalance_type=None,
    density_status=complexity.Status.CLEAN,
    rp_status=refactoring.Status.MINIMAL,
    oe_status=overengineering.Status.SIMPLE,
):
    """Build a Sources mock with pre-set statuses."""
    src = Sources.__new__(Sources)
    src._path = "/fake"
    src._lang = "python"
    src._packages = []
    src._modules = []
    src._classes = []
    src._methods = []
    src._functions = []

    metric = score.Metric(
        value=score_value,
        imbalance_type=imbalance_type,
    )

    src._status = type('obj', (object,), {
        'score': metric,
        'reasons': [],
        'suggestions': [],
        'name': metric.status,
    })()

    src.__dict__['complexity'] = type('obj', (object,), {
        'status': density_status,
        'density': 5.0,
    })()

    src.__dict__['refactoring_pressure'] = type('obj', (object,), {
        'status': rp_status,
        'score': 10,
    })()

    src._overengineering_pressure = type('obj', (object,), {
        'status': oe_status,
        'score': 10,
    })()

    return src


class TestAnalyzeSourcesHealthy:
    def test_no_reasons_when_healthy(self):
        src = _make_sources()
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert src.status.reasons == []


class TestAnalyzeSourcesDensityReasons:
    def test_spaghetti_adds_reason(self):
        src = _make_sources(
            score_value=85,
            score_status=score.Status.EMERGENCY,
            density_status=complexity.Status.SPAGHETTI,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("Excessively high" in r for r in src.status.reasons)

    def test_unreadable_adds_reason(self):
        """UNREADABLE is in the same tuple as SPAGHETTI — same reason."""
        src = _make_sources(
            score_value=85,
            score_status=score.Status.EMERGENCY,
            density_status=complexity.Status.UNREADABLE,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("Excessively high" in r for r in src.status.reasons)

    def test_very_dirty_adds_reason(self):
        """VERY_DIRTY is in the same tuple as DIRTY — same reason."""
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            density_status=complexity.Status.VERY_DIRTY,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("High concentration" in r for r in src.status.reasons)

    def test_dirty_adds_reason(self):
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            density_status=complexity.Status.DIRTY,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("High concentration" in r for r in src.status.reasons)

    def test_moderate_adds_reason(self):
        src = _make_sources(
            score_value=25,
            score_status=score.Status.NORMAL,
            density_status=complexity.Status.MODERATE,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("requires attention" in r for r in src.status.reasons)

    @pytest.mark.parametrize("density_status", [
        complexity.Status.CLEAN,
        complexity.Status.GOOD,
    ])
    def test_good_or_clean_no_density_reason(self, density_status):
        """CLEAN and GOOD densities don't produce any reason."""
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            density_status=density_status,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert not any("concentration" in r for r in src.status.reasons)


class TestAnalyzeSourcesRefactoringReasons:
    def test_extreme_rp_adds_reason(self):
        src = _make_sources(
            score_value=85,
            score_status=score.Status.EMERGENCY,
            rp_status=refactoring.Status.EXTREME,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("Excessive refactoring" in r for r in src.status.reasons)

    def test_high_rp_adds_reason(self):
        """HIGH is in the same tuple as EXTREME — same reason."""
        src = _make_sources(
            score_value=65,
            score_status=score.Status.CRITICAL,
            rp_status=refactoring.Status.HIGH,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("Excessive refactoring" in r for r in src.status.reasons)

    def test_medium_rp_adds_reason(self):
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            rp_status=refactoring.Status.MEDIUM,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("Increased refactoring" in r for r in src.status.reasons)

    def test_low_rp_no_reason(self):
        """LOW and MINIMAL don't produce refactoring reasons."""
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            rp_status=refactoring.Status.LOW,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert not any("refactoring" in r.lower() for r in src.status.reasons)


class TestAnalyzeSourcesOverengineeringReasons:
    def test_bloated_oe_adds_reason(self):
        src = _make_sources(
            score_value=85,
            score_status=score.Status.EMERGENCY,
            oe_status=overengineering.Status.BLOATED,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("Excessive abstraction" in r for r in src.status.reasons)

    def test_overengineered_oe_adds_reason(self):
        """OVERENGINEERED is in the same tuple as BLOATED — same reason."""
        src = _make_sources(
            score_value=65,
            score_status=score.Status.CRITICAL,
            oe_status=overengineering.Status.OVERENGINEERED,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("Excessive abstraction" in r for r in src.status.reasons)

    def test_complex_oe_adds_reason(self):
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            oe_status=overengineering.Status.COMPLEX,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("Approaching complexity" in r for r in src.status.reasons)


class TestAnalyzeSourcesImbalance:
    def test_spaghetti_imbalance_adds_reason(self):
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            imbalance_type=score.ImbalanceType.SPAGHETTI,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("spaghetti" in r for r in src.status.reasons)

    def test_overengineering_imbalance_adds_reason(self):
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            imbalance_type=score.ImbalanceType.OVERENGINEERING,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        assert any("overengineering" in r for r in src.status.reasons)

    def test_no_imbalance_type_no_reason(self):
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            imbalance_type=None,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        # Only non-imbalance reasons may appear (depends on density/rp/oe)
        assert not any("spaghetti" in r or "overengineering" in r for r in src.status.reasons)


class TestAnalyzeMultipleReasons:
    def test_combined_reasons(self):
        src = _make_sources(
            score_value=85,
            score_status=score.Status.EMERGENCY,
            imbalance_type=score.ImbalanceType.SPAGHETTI,
            density_status=complexity.Status.SPAGHETTI,
            rp_status=refactoring.Status.HIGH,
            oe_status=overengineering.Status.BLOATED,
        )
        analyzer = Analyzer(src)
        analyzer.analyze_sources()
        # At least: imbalance + density + refactoring + overengineering = 4
        assert len(src.status.reasons) >= 4


class TestAnalyzeMethod:
    def test_analyze_delegates_to_analyze_sources(self):
        src = _make_sources(
            score_value=45,
            score_status=score.Status.WARNING,
            density_status=complexity.Status.MODERATE,
        )
        analyzer = Analyzer(src)
        analyzer.analyze()
        assert any("requires attention" in r for r in src.status.reasons)
