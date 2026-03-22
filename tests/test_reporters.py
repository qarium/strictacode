import json
import textwrap

import pytest

from strictacode.reporters import TextReporter, JsonReporter
from strictacode.source import (
    Sources,
    Status,
    PackageSource,
    ModuleSource,
    ClassSource,
    MethodSource,
    FunctionSource,
)
from strictacode.calc import score, Complexity
from strictacode.calc.pressure import refactoring
from strictacode.calc.pressure import overengineering


def _make_module(tmp_path, name="mod.py", content=None):
    """Create a temp module file and return ModuleSource."""
    if content is None:
        content = textwrap.dedent("""\
            class Foo:
                def bar(self):
                    pass
            def baz():
                pass
        """)
    filepath = tmp_path / name
    filepath.write_text(content)
    return ModuleSource(str(filepath), comment_line_prefixes=["#"],
                        comment_code_blocks=[('"""', '"""')])


def _make_sources_with_data(tmp_path):
    """Build a minimal Sources with packages, modules, classes, etc."""
    mod = _make_module(tmp_path, "main.py")
    pkg = PackageSource(str(tmp_path))
    pkg.modules.append(mod)

    src = Sources.__new__(Sources)
    src._path = str(tmp_path)
    src._lang = "python"
    src._packages = [pkg]
    src._modules = [mod]

    # Create class/method
    cls = ClassSource(mod, "Foo", lineno=1, endline=4, complexity=2,
                      loc_from_methods=True,
                      comment_line_prefixes=["#"],
                      comment_code_blocks=[('"""', '"""')])
    method = MethodSource(mod, cls, "bar", lineno=2, endline=3, complexity=1,
                          comment_line_prefixes=["#"],
                          comment_code_blocks=[('"""', '"""')])
    cls.methods.append(method)
    mod.classes.append(cls)

    # Create function
    func = FunctionSource(mod, "baz", lineno=5, endline=6, complexity=0,
                          comment_line_prefixes=["#"],
                          comment_code_blocks=[('"""', '"""')])
    mod.functions.append(func)

    src._classes = [cls]
    src._methods = [method]
    src._functions = [func]

    # Set statuses
    src._status = Status(score=score.Metric(value=15))
    pkg._status = Status(score=score.Metric(value=10))
    mod._status = Status(score=score.Metric(value=12))
    cls._status = Status(score=score.Metric(value=8))
    method._status = Status(score=score.Metric(value=5))
    func._status = Status(score=score.Metric(value=3))

    # Set overengineering_pressure on Sources (required by reporters)
    src._overengineering_pressure = overengineering.Metric(20)

    # Cache complexity and refactoring_pressure on Sources
    src.__dict__['complexity'] = Complexity(score=10, loc=mod.loc, children=[
        Complexity(score=2, loc=cls.loc, children=[
            Complexity(score=1, loc=method.loc),
        ]),
        Complexity(score=0, loc=func.loc),
    ])
    src.__dict__['refactoring_pressure'] = refactoring.Metric(
        score=15,
        data=refactoring.Data(
            loc=mod.loc,
            max_complexity=2,
            p90_complexity=1,
            complexity_density=src.complexity.density,
        ),
    )

    # Cache complexity and refactoring_pressure on module
    mod.__dict__['complexity'] = Complexity(score=2, loc=mod.loc, children=[
        Complexity(score=2, loc=cls.loc, children=[
            Complexity(score=1, loc=method.loc),
        ]),
        Complexity(score=0, loc=func.loc),
    ])
    mod.__dict__['refactoring_pressure'] = refactoring.Metric(
        score=12,
        data=refactoring.Data(
            loc=mod.loc,
            max_complexity=2,
            p90_complexity=1,
            complexity_density=mod.complexity.density,
        ),
    )
    mod._overengineering_pressure = overengineering.Metric(10)

    # Cache complexity on class
    cls.__dict__['complexity'] = Complexity(score=2, loc=cls.loc, children=[
        Complexity(score=1, loc=method.loc),
    ])

    # Cache complexity on method
    method.__dict__['complexity'] = Complexity(score=1, loc=method.loc,
                                               total_sum=True)

    # Cache complexity on function
    func.__dict__['complexity'] = Complexity(score=0, loc=func.loc,
                                             total_sum=True)

    return src


# ---------------------------------------------------------------------------
# BaseReporter
# ---------------------------------------------------------------------------


class TestBaseReporterOutput:
    def test_output_to_file(self, tmp_path):
        src = _make_sources_with_data(tmp_path)
        output_path = tmp_path / "report.txt"

        reporter = TextReporter(src, output=str(output_path))
        reporter.report()

        assert output_path.exists()
        content = output_path.read_text()
        assert "Project:" in content
        assert "lang:" in content

    def test_output_to_stdout(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = TextReporter(src, output=None)
        reporter.report()

        captured = capsys.readouterr()
        assert "Project:" in captured.out


# ---------------------------------------------------------------------------
# TextReporter
# ---------------------------------------------------------------------------


class TestTextReporter:
    def test_project_report(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = TextReporter(src, short=True)
        reporter.report()

        captured = capsys.readouterr()
        assert "Project:" in captured.out
        assert "lang: python" in captured.out
        assert "status:" in captured.out
        assert "healthy" in captured.out

    def test_short_mode_no_packages(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = TextReporter(src, short=True)
        reporter.report()

        captured = capsys.readouterr()
        assert "Project:" in captured.out
        assert "Packages:" not in captured.out

    def test_full_mode_includes_packages(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = TextReporter(src, short=False)
        reporter.report()

        captured = capsys.readouterr()
        assert "Packages:" in captured.out
        assert "Modules:" in captured.out

    def test_details_mode_includes_classes(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = TextReporter(src, short=False, details=True)
        reporter.report()

        captured = capsys.readouterr()
        assert "Classes:" in captured.out
        assert "Methods:" in captured.out
        assert "Functions:" in captured.out

    def test_reasons_displayed(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)
        src._status.reasons.append("Test reason")

        reporter = TextReporter(src, short=True)
        reporter.report()

        captured = capsys.readouterr()
        assert "Test reason" in captured.out

    def test_suggestions_displayed(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)
        src._status.suggestions.append("Test suggestion")

        reporter = TextReporter(src, short=True)
        reporter.report()

        captured = capsys.readouterr()
        assert "Test suggestion" in captured.out


# ---------------------------------------------------------------------------
# JsonReporter
# ---------------------------------------------------------------------------


class TestJsonReporter:
    def test_output_valid_json(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = JsonReporter(src, short=True)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "project" in data

    def test_project_keys(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = JsonReporter(src, short=True)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        project = data["project"]

        assert project["lang"] == "python"
        assert isinstance(project["loc"], int)
        assert project["loc"] > 0
        assert project["packages"] == 1
        assert project["modules"] == 1
        assert project["classes"] == 1
        assert project["methods"] == 1
        assert project["functions"] == 1
        assert project["status"]["score"] == 15
        assert isinstance(project["status"]["name"], str)
        assert project["status"]["reasons"] == []
        assert project["status"]["suggestions"] == []
        assert project["complexity"]["score"] == 10
        assert isinstance(project["complexity"]["density"], float)
        assert project["refactoring_pressure"]["score"] == 15
        assert project["overengineering_pressure"]["score"] == 20

    def test_short_mode_no_packages(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = JsonReporter(src, short=True)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "packages" not in data

    def test_full_mode_includes_packages(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = JsonReporter(src, short=False)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "packages" in data
        assert "modules" in data

    def test_details_mode_includes_classes(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)

        reporter = JsonReporter(src, short=False, details=True)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "classes" in data
        assert "methods" in data
        assert "functions" in data

    def test_reasons_in_json(self, tmp_path, capsys):
        src = _make_sources_with_data(tmp_path)
        src._status.reasons.append("Test reason")

        reporter = JsonReporter(src, short=True)
        reporter.report()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "Test reason" in data["project"]["status"]["reasons"]

    def test_output_to_file(self, tmp_path):
        src = _make_sources_with_data(tmp_path)
        output_path = tmp_path / "report.json"

        reporter = JsonReporter(src, short=True, output=str(output_path))
        reporter.report()

        data = json.loads(output_path.read_text())
        assert "project" in data
