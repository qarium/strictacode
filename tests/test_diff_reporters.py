import json

from strictacode.reporters import JsonDiffReporter, TextDiffReporter
from strictacode.statistics import ProjectDiff, ProjectStat


def _make_diff(*, score=(10, 20), density=(5.0, 7.5), rp=(8, 4), op=(3, 7)):
    stat_a = ProjectStat(
        name="baseline",
        score=score[0],
        complexity_density=density[0],
        refactoring_pressure=rp[0],
        overengineering_pressure=op[0],
    )
    stat_b = ProjectStat(
        name="current",
        score=score[1],
        complexity_density=density[1],
        refactoring_pressure=rp[1],
        overengineering_pressure=op[1],
    )
    return ProjectDiff(stat_a, stat_b)


# ---------------------------------------------------------------------------
# TextDiffReporter
# ---------------------------------------------------------------------------


class TestTextDiffReporter:
    def test_basic_diff_output(self, capsys):
        diff = _make_diff()
        reporter = TextDiffReporter(diff)
        reporter.report()

        captured = capsys.readouterr()
        assert "Diff:" in captured.out
        assert "score: 10" in captured.out
        assert "complexity_density: 2.5" in captured.out
        assert "refactoring_pressure: 4" in captured.out
        assert "overengineering_pressure: 4" in captured.out

    def test_no_details_hides_results(self, capsys):
        diff = _make_diff()
        reporter = TextDiffReporter(diff, details=False)
        reporter.report()

        captured = capsys.readouterr()
        assert "Baseline" not in captured.out
        assert "Current" not in captured.out

    def test_details_shows_results(self, capsys):
        diff = _make_diff(score=(10, 20))
        reporter = TextDiffReporter(diff, details=True)
        reporter.report()

        captured = capsys.readouterr()
        assert "Baseline" in captured.out
        assert "Current" in captured.out
        assert "score: 10" in captured.out
        assert "score: 20" in captured.out

    def test_output_to_file(self, tmp_path):
        diff = _make_diff()
        output_path = tmp_path / "diff.txt"
        reporter = TextDiffReporter(diff, output=str(output_path))
        reporter.report()

        content = output_path.read_text()
        assert "Diff:" in content


# ---------------------------------------------------------------------------
# JsonDiffReporter
# ---------------------------------------------------------------------------


class TestJsonDiffReporter:
    def test_valid_json_output(self, capsys):
        diff = _make_diff()
        reporter = JsonDiffReporter(diff)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "diff" in data

    def test_diff_keys(self, capsys):
        diff = _make_diff()
        reporter = JsonDiffReporter(diff)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        d = data["diff"]
        assert d["score"] == 10
        assert d["complexity_density"] == 2.5
        assert d["refactoring_pressure"] == 4
        assert d["overengineering_pressure"] == 4

    def test_no_details_hides_results(self, capsys):
        diff = _make_diff()
        reporter = JsonDiffReporter(diff, details=False)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "baseline" not in data
        assert "current" not in data

    def test_details_includes_results(self, capsys):
        diff = _make_diff(score=(10, 20))
        reporter = JsonDiffReporter(diff, details=True)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "baseline" in data
        assert "current" in data
        assert data["baseline"]["score"] == 10
        assert data["current"]["score"] == 20

    def test_output_to_file(self, tmp_path):
        diff = _make_diff()
        output_path = tmp_path / "diff.json"
        reporter = JsonDiffReporter(diff, output=str(output_path))
        reporter.report()

        data = json.loads(output_path.read_text())
        assert "diff" in data
