import json
import textwrap

from click.testing import CliRunner
from strictacode.__main__ import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# compare command
# ---------------------------------------------------------------------------


class TestCompareCommand:
    def _write_json_report(self, tmp_path, name, *, score=10, density=5.0, rp=8, op=5):
        data = {
            "project": {
                "status": {"score": score},
                "complexity": {"density": density},
                "refactoring_pressure": {"score": rp},
                "overengineering_pressure": {"score": op},
            }
        }
        path = tmp_path / name
        path.write_text(json.dumps(data))
        return str(path)

    def test_compare_two_reports(self, tmp_path):
        report1 = self._write_json_report(tmp_path, "r1.json", score=10, density=5.0)
        report2 = self._write_json_report(tmp_path, "r2.json", score=20, density=10.0)

        result = runner.invoke(app, ["compare", report1, report2])
        assert result.exit_code == 0
        assert "Diff:" in result.output

    def test_compare_with_threshold_pass(self, tmp_path):
        report1 = self._write_json_report(tmp_path, "r1.json", score=10)
        report2 = self._write_json_report(tmp_path, "r2.json", score=59)

        result = runner.invoke(app, ["compare", report1, report2, "--threshold", "SCORE=50"])
        assert result.exit_code == 0
        assert "FAIL" not in result.output

    def test_compare_with_threshold_fail(self, tmp_path):
        report1 = self._write_json_report(tmp_path, "r1.json", score=10)
        report2 = self._write_json_report(tmp_path, "r2.json", score=61)

        result = runner.invoke(app, ["compare", report1, report2, "--threshold", "SCORE=50"])
        assert result.exit_code == 1
        assert "FAIL" in result.output

    def test_compare_shows_both_results(self, tmp_path):
        report1 = self._write_json_report(tmp_path, "r1.json", score=15)
        report2 = self._write_json_report(tmp_path, "r2.json", score=25)

        result = runner.invoke(app, ["compare", report1, report2])
        assert "r1.json" in result.output
        assert "r2.json" in result.output
        assert "Score: 15" in result.output
        assert "Score: 25" in result.output

    def test_compare_nonexistent_file(self, tmp_path):
        report1 = self._write_json_report(tmp_path, "r1.json")
        report2 = str(tmp_path / "nonexistent.json")

        result = runner.invoke(app, ["compare", report1, report2])
        assert result.exit_code != 0
        assert result.exception is not None


# ---------------------------------------------------------------------------
# install agent-skill command
# ---------------------------------------------------------------------------


class TestInstallAgentSkill:
    def test_install_claude(self, tmp_path, monkeypatch):
        def mock_install(skill_name, agent):
            return "/mock/path/skill/SKILL.md"

        monkeypatch.setattr("strictacode.__main__.skill.install", mock_install)

        result = runner.invoke(app, ["install", "agent-skill", "--agent", "claude"])
        assert result.exit_code == 0
        assert "Successfully installed" in result.output
        assert "/mock/path/skill/SKILL.md" in result.output

    def test_install_cursor(self, tmp_path, monkeypatch):
        def mock_install(skill_name, agent):
            return "/mock/path/skill/SKILL.md"

        monkeypatch.setattr("strictacode.__main__.skill.install", mock_install)

        result = runner.invoke(app, ["install", "agent-skill", "--agent", "cursor"])
        assert result.exit_code == 0

    def test_install_custom_name(self, tmp_path, monkeypatch):
        def mock_install(skill_name, agent):
            return f"/mock/{skill_name}/SKILL.md"

        monkeypatch.setattr("strictacode.__main__.skill.install", mock_install)

        result = runner.invoke(
            app,
            [
                "install",
                "agent-skill",
                "--agent",
                "claude",
                "--name",
                "custom-name",
            ],
        )
        assert result.exit_code == 0
        assert "custom-name" in result.output


# ---------------------------------------------------------------------------
# analyze command
# ---------------------------------------------------------------------------


class TestAnalyzeCommand:
    def test_nonexistent_path(self):
        result = runner.invoke(app, ["analyze", "/nonexistent/path/xyz"])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_file_instead_of_directory(self, tmp_path):
        f = tmp_path / "file.py"
        f.write_text("pass")
        result = runner.invoke(app, ["analyze", str(f)])
        assert result.exit_code != 0
        assert "not a directory" in result.output

    def test_unknown_language(self, tmp_path):
        # Only non-source files — no detectable language
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "notes.md").write_text("# notes")
        result = runner.invoke(app, ["analyze", str(tmp_path)])
        assert result.exit_code != 0
        assert "Unknown program language" in result.output

    def test_analyze_json_format(self, tmp_path):
        """Smoke test: analyze a minimal Python project with --format json."""
        (tmp_path / "main.py").write_text(
            textwrap.dedent("""\
            def hello():
                return "world"
        """)
        )
        result = runner.invoke(
            app,
            [
                "analyze",
                str(tmp_path),
                "--format",
                "json",
                "--short",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "project" in data
        assert data["project"]["lang"] == "python"

    def test_analyze_text_format(self, tmp_path):
        """Smoke test: analyze a minimal Python project with text output."""
        (tmp_path / "main.py").write_text(
            textwrap.dedent("""\
            def hello():
                return "world"
        """)
        )
        result = runner.invoke(
            app,
            [
                "analyze",
                str(tmp_path),
                "--short",
            ],
        )
        assert result.exit_code == 0
        assert "Project:" in result.output
        assert "python" in result.output.lower()
