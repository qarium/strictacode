import textwrap

import pytest
from strictacode.utils import (
    _parse_gitignore,
    _should_exclude,
    detect_language,
    detect_languages,
    ignore_dirs,
    lines_of_code,
    redirect_output,
    source_content,
)

# ---------------------------------------------------------------------------
# lines_of_code
# ---------------------------------------------------------------------------


class TestLinesOfCode:
    def test_simple_file_with_code_lines(self, tmp_py_file):
        """Non-blank lines are counted (comments counted when no ignore_prefixes)."""
        # tmp_py_file has 1 comment + 8 code lines + 1 blank line = 9 non-blank
        assert lines_of_code(tmp_py_file) == 9

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.py"
        path.write_text("")
        assert lines_of_code(str(path)) == 0

    def test_file_with_only_comments_and_blanks(self, tmp_path):
        path = tmp_path / "comments.py"
        path.write_text(
            textwrap.dedent("""\
            # first comment
            # second comment

            # trailing comment
        """)
        )
        assert lines_of_code(str(path), ignore_prefixes=["#"]) == 0

    def test_with_lineno_endline_range(self, tmp_py_file):
        """Only lines within [lineno, endline] are considered."""
        # Lines 1-10 in tmp_py_file:
        #  1: # comment        (ignored - comment)
        #  2: def foo():       (counted)
        #  3:     x = 1        (counted)
        #  4:     return x      (counted)
        #  5:                   (blank)
        #  6: def bar():       (counted)
        #  7:     y = 2        (counted)
        #  8:     if y > 0:    (counted)
        #  9:         return y  (counted)
        # 10:     return 0      (counted)
        assert lines_of_code(tmp_py_file, lineno=6, endline=8) == 3

    def test_with_ignore_blocks_triple_quotes(self, tmp_path):
        path = tmp_path / "docstring.py"
        path.write_text(
            textwrap.dedent("""\
            def func():
                pass

            \"\"\"
            This whole block
            should be ignored.
            \"\"\"

            x = 1
        """)
        )
        # Opening/closing markers and content inside are all skipped.
        # Only: def func() + pass + x = 1 = 3
        assert lines_of_code(str(path), ignore_blocks=[('"""', '"""')]) == 3

    def test_ignore_blocks_two_consecutive_blocks(self, tmp_path):
        path = tmp_path / "two_blocks.py"
        path.write_text(
            textwrap.dedent("""\
            def func():
                pass

            \"\"\"
            first block
            \"\"\"

            \"\"\"
            second block
            \"\"\"

            x = 1
        """)
        )
        # Two separate blocks ignored. Only: def func() + pass + x = 1 = 3
        assert lines_of_code(str(path), ignore_blocks=[('"""', '"""')]) == 3

    def test_ignore_blocks_nested_opening_inside_block(self, tmp_path):
        path = tmp_path / "edge_case.py"
        path.write_text(
            textwrap.dedent("""\
            def func():
                pass

            \"\"\"
            \"\"\"abc
            \"\"\"

            x = 1
        """)
        )
        # Line \"\"\"abc starts with \"\"\" — opens a nested block (no closing).
        # So \"\"\" (the standalone line) closes the outer block.
        # Result: def func() + pass + x = 1 = 3... BUT \"\"\"abc is counted
        # as start of new block (never closed), so the standalone \"\"\" line
        # becomes content, not a closing marker.
        # Actual: def func() + pass + \"\"\"abc + x = 1 = 4... let's check.
        result = lines_of_code(str(path), ignore_blocks=[('"""', '"""')])
        # After bugfix: block starts at first \"\"\", line \"\"\"abc opens nested block
        # (stop_pointer becomes '"""' for nested), standalone \"\"\" closes nested,
        # but outer block never closes — so all lines after block start are skipped.
        # Actual result: def func() + pass = 2
        assert result == 2

    def test_combined_ignore_prefixes_and_blocks(self, tmp_path):
        path = tmp_path / "mixed.py"
        path.write_text(
            textwrap.dedent("""\
            # top comment
            def hello():
                pass

            \"\"\"
            Docstring block
            ignored here.
            \"\"\"

            # another comment
            y = 2
        """)
        )
        # Comments filtered by ignore_prefixes. Block fully ignored.
        # Counted: def hello() + pass + y = 2 = 3
        assert (
            lines_of_code(
                str(path),
                ignore_prefixes=["#"],
                ignore_blocks=[('"""', '"""')],
            )
            == 3
        )


# ---------------------------------------------------------------------------
# _parse_gitignore
# ---------------------------------------------------------------------------


class TestParseGitignore:
    def test_no_gitignore(self, tmp_path):
        assert _parse_gitignore(str(tmp_path)) == []

    def test_with_patterns(self, tmp_path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("dist\nbuild\n*.egg-info\n")
        patterns = _parse_gitignore(str(tmp_path))
        assert patterns == ["dist", "build", "*.egg-info"]

    def test_comments_skipped(self, tmp_path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("# this is a comment\ndist\n")
        patterns = _parse_gitignore(str(tmp_path))
        assert patterns == ["dist"]

    def test_empty_lines_skipped(self, tmp_path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("\ndist\n\nbuild\n\n")
        patterns = _parse_gitignore(str(tmp_path))
        assert patterns == ["dist", "build"]


# ---------------------------------------------------------------------------
# _should_exclude
# ---------------------------------------------------------------------------


class TestShouldExclude:
    @pytest.mark.parametrize(
        ("name", "patterns", "expected"),
        [
            ("dist", ["dist", "build"], True),
            ("dist", ["di*", "build"], True),
            ("src", ["dist", "build"], False),
            ("dist", ["dist/"], True),
        ],
    )
    def test_should_exclude(self, name, patterns, expected):
        assert _should_exclude(name, patterns) is expected


# ---------------------------------------------------------------------------
# ignore_dirs
# ---------------------------------------------------------------------------


class TestIgnoreDirs:
    def test_gitignore_excluded_dirs(self, tmp_project_with_gitignore):
        excluded = ignore_dirs(str(tmp_project_with_gitignore))
        assert "dist" in excluded
        assert "build" in excluded

    def test_explicit_exclude_patterns(self, tmp_path):
        (tmp_path / "dist").mkdir()
        (tmp_path / "src").mkdir()
        excluded = ignore_dirs(str(tmp_path), exclude_patterns=["dist"])
        assert "dist" in excluded
        assert "src" not in excluded


# ---------------------------------------------------------------------------
# source_content
# ---------------------------------------------------------------------------


class TestSourceContent:
    def test_read_specific_range(self, tmp_py_file):
        content = source_content(tmp_py_file, 2, 4)
        # source_content joins raw lines (each ending with \n) using \n,
        # producing: "def foo():\n\n    x = 1\n\n    return x\n"
        assert "def foo():" in content
        assert "    x = 1" in content
        assert "    return x" in content
        assert "def bar():" not in content

    def test_single_line(self, tmp_py_file):
        content = source_content(tmp_py_file, 2, 2)
        assert content == "def foo():\n"

    def test_lineno_beyond_file_length(self, tmp_py_file):
        content = source_content(tmp_py_file, 999, 1000)
        assert content == ""

    def test_lineno_greater_than_endline_returns_empty(self, tmp_py_file):
        content = source_content(tmp_py_file, 5, 3)
        assert content == ""


# ---------------------------------------------------------------------------
# detect_languages
# ---------------------------------------------------------------------------


class TestDetectLanguages:
    def test_directory_with_python_files(self, tmp_path):
        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.py").write_text("pass")
        langs = detect_languages(str(tmp_path))
        assert langs == ["python"]

    def test_mixed_python_and_go(self, tmp_path):
        (tmp_path / "main.py").write_text("pass")
        (tmp_path / "lib.go").write_text("package main")
        langs = detect_languages(str(tmp_path))
        assert "python" in langs
        assert "golang" in langs

    def test_empty_directory(self, tmp_path):
        langs = detect_languages(str(tmp_path))
        assert langs == []

    def test_respects_gitignore(self, tmp_path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("excluded\n")
        excluded_dir = tmp_path / "excluded"
        excluded_dir.mkdir()
        (excluded_dir / "ignored.go").write_text("package main")
        (tmp_path / "main.py").write_text("pass")
        langs = detect_languages(str(tmp_path))
        assert "python" in langs
        assert "golang" not in langs

    def test_javascript_files_detected(self, tmp_path):
        (tmp_path / "app.js").write_text("console.log()")
        (tmp_path / "util.ts").write_text("export {}")
        langs = detect_languages(str(tmp_path))
        assert "javascript" in langs


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    def test_directory_with_python_files(self, tmp_path):
        (tmp_path / "a.py").write_text("pass")
        assert detect_language(str(tmp_path)) == "python"

    def test_more_python_than_go(self, tmp_path):
        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.py").write_text("pass")
        (tmp_path / "c.go").write_text("package main")
        assert detect_language(str(tmp_path)) == "python"

    def test_empty_directory(self, tmp_path):
        assert detect_language(str(tmp_path)) is None


# ---------------------------------------------------------------------------
# redirect_output
# ---------------------------------------------------------------------------


class TestRedirectOutput:
    def test_stdout_redirected_to_file(self, tmp_path):
        output_path = tmp_path / "out.txt"
        with redirect_output(str(output_path)):
            print("hello")
        assert "hello" in output_path.read_text()

    def test_stderr_redirected_to_file(self, tmp_path):
        output_path = tmp_path / "err.txt"
        with redirect_output(str(output_path)):
            import sys

            sys.stderr.write("error msg\n")
        assert "error msg" in output_path.read_text()

    def test_restore_after_context(self, tmp_path, capsys):
        output_path = tmp_path / "out.txt"
        with redirect_output(str(output_path)):
            print("redirected")
        print("restored")
        captured = capsys.readouterr()
        assert "redirected" not in captured.out
        assert "restored" in captured.out

    def test_restore_after_exception(self, tmp_path, capsys):
        output_path = tmp_path / "out.txt"
        try:
            with redirect_output(str(output_path)):
                print("before error")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        print("after error")
        captured = capsys.readouterr()
        assert "before error" not in captured.out
        assert "after error" in captured.out
