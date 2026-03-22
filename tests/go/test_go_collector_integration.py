"""Integration tests for Go collector — runs real `go run` on temp .go files."""

import shutil
import textwrap

import pytest

from strictacode.go.collector import collect


# ---------------------------------------------------------------------------
# Skip when Go is not available
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    shutil.which("go") is None,
    reason="requires go",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_go(tmp_path, name, code):
    """Write a .go package directory and return collect() result."""
    pkg = tmp_path / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "main.go").write_text(textwrap.dedent(code))
    return collect(str(pkg))


def _single_go(tmp_path, code):
    """Write a single .go file and return collect() result."""
    return _write_go(tmp_path, "pkg", code)


def _find_item(result, name):
    """Find item(s) by name across all files in the result."""
    for _file, items in result.items():
        for item in items:
            if item["name"] == name:
                return item
    return None


def _find_structure(result, name):
    item = _find_item(result, name)
    assert item is not None, f"struct '{name}' not found"
    assert item["type"] == "structure"
    return item


def _find_function(result, name):
    item = _find_item(result, name)
    assert item is not None, f"function '{name}' not found"
    assert item["type"] == "function"
    return item


# ===========================================================================
# Complexity tests
# ===========================================================================


class TestBasicComplexity:
    def test_empty_function(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            func f() int { return 42 }
        """)
        _find_function(r, "f")["complexity"] == 1

    def test_single_if(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            func g(x int) int {
                if x > 0 { return x }
                return -1
            }
        """)
        assert _find_function(r, "g")["complexity"] == 2

    def test_for_loop(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            func loop() {
                for i := 0; i < 10; i++ {}
            }
        """)
        assert _find_function(r, "loop")["complexity"] == 2

    def test_range_loop(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            func iter(items []int) {
                for _, v := range items {}
            }
        """)
        assert _find_function(r, "iter")["complexity"] == 2

    def test_switch_cases(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            func sw(x int) int {
                switch x {
                case 1: return 1
                case 2: return 2
                default: return 0
                }
            }
        """)
        # 1 (base) + 1 (SwitchStmt) + 3 (CaseClause: 2 cases + default) = 5
        assert _find_function(r, "sw")["complexity"] == 5

    def test_select(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            func sel(ch chan int) {
                select {
                case <-ch:
                }
            }
        """)
        # 1 (base) + 1 (SelectStmt) = 2
        # CommClause in select is not CaseClause, so no extra +1
        assert _find_function(r, "sel")["complexity"] == 2

    def test_go_and_defer(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            func run() {
                go func() {}()
                defer func() {}()
            }
        """)
        # 1 (base) + 1 (go) + 1 (defer) = 3
        assert _find_function(r, "run")["complexity"] == 3

    def test_logical_and_or(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            func logic(a, b bool) {
                if a && b {}
                if a || b {}
            }
        """)
        # 1 (base) + 1 (if) + 1 (&&) + 1 (if) + 1 (||) = 5
        assert _find_function(r, "logic")["complexity"] == 5


class TestStructuresAndClosures:
    def test_structure_complexity(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            type S struct{}
            func (s S) add(a, b int) int { return a + b }
            func (s S) check(x int) bool { if x > 0 { return true }; return false }
        """)
        s = _find_structure(r, "S")
        # add(1) + check(2) = 3
        assert s["complexity"] == 3
        assert len(s["methods"]) == 2

    def test_pointer_receiver(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            type Counter struct{}
            func (c *Counter) inc() {}
            func (c Counter) val() int { return 0 }
        """)
        c = _find_structure(r, "Counter")
        assert c["complexity"] == 2
        assert len(c["methods"]) == 2

    def test_closures(self, tmp_path):
        r = _single_go(tmp_path, """\
            package main
            func wrap() {
                fn := func(x int) {
                    if x > 0 {}
                }
                _ = fn
            }
        """)
        wrap = _find_function(r, "wrap")
        # ast.Inspect recurses into FuncLit, so wrap complexity = 1 (base) + 1 (if) = 2
        assert wrap["complexity"] == 2
        assert len(wrap["closures"]) == 1
        closure = wrap["closures"][0]
        assert closure["name"] == "closure"
        assert closure["complexity"] == 2


# ===========================================================================
# File filtering
# ===========================================================================


class TestFiltering:
    def test_file_filtering(self, tmp_path):
        """_test.go files and vendor/ are excluded."""
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "main.go").write_text(textwrap.dedent("""\
            package main
            func Main() int { return 0 }
        """))
        (pkg / "main_test.go").write_text(textwrap.dedent("""\
            package main
            func TestMain() {}
        """))
        vendor = tmp_path / "vendor"
        vendor.mkdir()
        (vendor / "dep.go").write_text(textwrap.dedent("""\
            package vendor
            func Dep() {}
        """))
        r = collect(str(tmp_path))
        assert "pkg/main.go" in r
        assert "pkg/main_test.go" not in r
        # vendor dir is skipped entirely
        assert "vendor/dep.go" not in r
