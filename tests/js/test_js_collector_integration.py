"""Integration tests for JS collector — runs real node + babel on temp JS files."""

import shutil
import subprocess
import textwrap

import pytest

from strictacode.js.collector import collect


# ---------------------------------------------------------------------------
# Skip when node or babel is not available
# ---------------------------------------------------------------------------


def _babel_available():
    if shutil.which("node") is None:
        return False
    try:
        result = subprocess.run(
            ["node", "-e", "require('@babel/parser'); require('@babel/traverse')"],
            capture_output=True,
            text=True,
            env=_node_env(),
        )
        return result.returncode == 0
    except Exception:
        return False


def _node_env():
    import os
    import sys

    env = os.environ.copy()
    local_root = subprocess.check_output(["npm", "root"], text=True).strip()
    global_root = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    env["NODE_PATH"] = (";" if sys.platform == "win32" else ":").join(
        [local_root, global_root]
    )
    return env


pytestmark = pytest.mark.skipif(
    not _babel_available(),
    reason="requires node with @babel/parser and @babel/traverse",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_js(tmp_path, name, code):
    """Write a .js file into *tmp_path* and return its directory."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.js").write_text(textwrap.dedent(code))
    return str(d)


def _single_func(tmp_path, code):
    """Write a single .js file and return collect() result dict."""
    d = _write_js(tmp_path, "src", code)
    return collect(d)


def _assert_complexity(result, name, expected):
    items = result.get("index.js", [])
    matches = [i for i in items if i["name"] == name]
    assert len(matches) == 1, f"expected 1 item '{name}', got {len(matches)}"
    assert matches[0]["complexity"] == expected, (
        f"expected complexity {expected} for '{name}', got {matches[0]['complexity']}"
    )


# ===========================================================================
# Complexity tests
# ===========================================================================


class TestBasicComplexity:
    def test_empty_function(self, tmp_path):
        r = _single_func(tmp_path, "function f() { return 1 }\n")
        _assert_complexity(r, "f", 1)

    def test_single_if(self, tmp_path):
        r = _single_func(tmp_path, "function f(x) { if (x > 0) return x; return -1; }\n")
        _assert_complexity(r, "f", 2)

    def test_if_else_if(self, tmp_path):
        r = _single_func(tmp_path, """\
            function f(x) {
                if (x > 0) return 1;
                else if (x < 0) return -1;
                return 0;
            }
        """)
        _assert_complexity(r, "f", 3)

    def test_for_loop(self, tmp_path):
        r = _single_func(tmp_path, "function f() { for (let i = 0; i < 10; i++) {} }\n")
        _assert_complexity(r, "f", 2)

    def test_for_in(self, tmp_path):
        r = _single_func(tmp_path, "function f(obj) { for (const k in obj) {} }\n")
        _assert_complexity(r, "f", 2)

    def test_for_of(self, tmp_path):
        r = _single_func(tmp_path, "function f(arr) { for (const v of arr) {} }\n")
        _assert_complexity(r, "f", 2)

    def test_while_loop(self, tmp_path):
        r = _single_func(tmp_path, "function f() { let n = 5; while (n > 0) { n--; } }\n")
        _assert_complexity(r, "f", 2)

    def test_do_while(self, tmp_path):
        r = _single_func(tmp_path, "function f() { let n = 5; do { n--; } while (n > 0); }\n")
        _assert_complexity(r, "f", 2)

    def test_try_catch(self, tmp_path):
        r = _single_func(tmp_path, "function f() { try { risky(); } catch(e) { fallback(); } }\n")
        _assert_complexity(r, "f", 2)

    def test_ternary(self, tmp_path):
        r = _single_func(tmp_path, "function f(x) { return x > 0 ? x : -x; }\n")
        _assert_complexity(r, "f", 2)

    def test_logical_and(self, tmp_path):
        r = _single_func(tmp_path, "function f(a, b) { if (a && b) return true; }\n")
        _assert_complexity(r, "f", 3)

    def test_logical_or(self, tmp_path):
        r = _single_func(tmp_path, "function f(a, b) { if (a || b) return true; }\n")
        _assert_complexity(r, "f", 3)

    def test_combined_logical(self, tmp_path):
        r = _single_func(tmp_path, "function f(a, b, c) { if (a && b || c) return true; }\n")
        _assert_complexity(r, "f", 4)

    def test_switch_cases(self, tmp_path):
        r = _single_func(tmp_path, """\
            function f(x) {
                switch(x) {
                    case 1: return "one";
                    case 2: return "two";
                    case 3: return "three";
                    default: return "other";
                }
            }
        """)
        # 4 SwitchCase including default (+4), no extra for SwitchStatement
        _assert_complexity(r, "f", 5)


class TestClassAndClosures:
    def test_class_complexity(self, tmp_path):
        r = _single_func(tmp_path, """\
            class Calculator {
                add(a, b) { return a + b; }
                divide(a, b) { if (b === 0) throw new Error(); return a / b; }
            }
        """)
        items = r.get("index.js", [])
        cls = [i for i in items if i["name"] == "Calculator"]
        assert len(cls) == 1
        # class complexity = sum of methods: add(1) + divide(2) = 3
        assert cls[0]["complexity"] == 3
        assert cls[0]["type"] == "class"

    def test_closures(self, tmp_path):
        r = _single_func(tmp_path, """\
            function outer() {
                var inner = function() {
                    if (true) return 1;
                    return 0;
                };
                inner();
            }
        """)
        items = r.get("index.js", [])
        outer = [i for i in items if i["name"] == "outer"]
        assert len(outer) == 1
        # calculateComplexity skips nested functions (matches radon behavior),
        # so outer complexity = 1 (base only)
        assert outer[0]["complexity"] == 1
        assert len(outer[0]["closures"]) == 1
        assert outer[0]["closures"][0]["name"] == "inner"
        assert outer[0]["closures"][0]["complexity"] == 2

    def test_method_closures(self, tmp_path):
        r = _single_func(tmp_path, """\
            class Filter {
                process(items) {
                    const fn = function(item) {
                        if (item > 0) return true;
                        return false;
                    };
                    items.filter(fn);
                }
            }
        """)
        items = r.get("index.js", [])
        cls = [i for i in items if i["name"] == "Filter"]
        assert len(cls) == 1
        methods = cls[0]["methods"]
        assert len(methods) == 1
        process = methods[0]
        assert process["name"] == "process"
        # calculateComplexity skips nested functions (matches radon behavior),
        # so process complexity = 1 (base only)
        assert process["complexity"] == 1
        assert len(process["closures"]) == 1
        closure = process["closures"][0]
        assert closure["name"] == "fn"
        assert closure["complexity"] == 2


# ===========================================================================
# File / directory filtering
# ===========================================================================


class TestFiltering:
    def test_file_filtering_prefix(self, tmp_path):
        """Files starting with 'test' are ignored."""
        (tmp_path / "test_helper.js").write_text("function f() {}\n")
        (tmp_path / "app.js").write_text("function g() {}\n")
        r = collect(str(tmp_path))
        assert "test_helper.js" not in r
        assert "app.js" in r

    def test_file_filtering_suffix(self, tmp_path):
        """Files ending with .test.js / .spec.js are ignored."""
        (tmp_path / "app.test.js").write_text("function f() {}\n")
        (tmp_path / "app.spec.js").write_text("function g() {}\n")
        (tmp_path / "app.js").write_text("function h() {}\n")
        r = collect(str(tmp_path))
        assert "app.test.js" not in r
        assert "app.spec.js" not in r
        assert "app.js" in r

    def test_directory_filtering(self, tmp_path):
        """Directories like node_modules/ and .git/ are ignored."""
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "dep.js").write_text("function dep() {}\n")
        git = tmp_path / ".git"
        git.mkdir()
        (git / "hook.js").write_text("function hook() {}\n")
        (tmp_path / "app.js").write_text("function main() {}\n")
        r = collect(str(tmp_path))
        assert len(r) == 1
        assert "app.js" in r
