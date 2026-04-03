"""Integration tests for Kotlin collector — pure Python + tree-sitter."""

import textwrap

from strictacode.kotlin.collector import collect


def _write_kt(tmp_path, name, code):
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "Main.kt").write_text(textwrap.dedent(code))
    return collect(str(d))


def _single_kt(tmp_path, code):
    return _write_kt(tmp_path, "pkg", code)


def _find_item(result, name):
    for _file, items in result.items():
        for item in items:
            if item["name"] == name:
                return item
    return None


def _find_class(result, name):
    item = _find_item(result, name)
    assert item is not None, f"class '{name}' not found"
    assert item["type"] == "class"
    return item


def _find_function(result, name):
    item = _find_item(result, name)
    assert item is not None, f"function '{name}' not found"
    assert item["type"] == "function"
    return item


class TestBasicComplexity:
    def test_empty_function_expression_body(self, tmp_path):
        r = _single_kt(tmp_path, "fun f(): Int = 42\n")
        assert _find_function(r, "f")["complexity"] == 1

    def test_empty_function_block_body(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            fun f() {
            }
        """,
        )
        assert _find_function(r, "f")["complexity"] == 1

    def test_single_if(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            fun g(x: Int): Int {
                if (x > 0) return x
                return -1
            }
        """,
        )
        assert _find_function(r, "g")["complexity"] == 2

    def test_for_loop(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            fun loop(items: List<Int>) {
                for (item in items) {}
            }
        """,
        )
        assert _find_function(r, "loop")["complexity"] == 2

    def test_while_loop(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            fun w() {
                var x = 10
                while (x > 0) { x-- }
            }
        """,
        )
        assert _find_function(r, "w")["complexity"] == 2

    def test_when_branches(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            fun sw(x: Int): String {
                return when (x) {
                    1 -> "one"
                    2 -> "two"
                    else -> "other"
                }
            }
        """,
        )
        # 1 (base) + 2 (non-else when entries) = 3
        assert _find_function(r, "sw")["complexity"] == 3

    def test_logical_and_or(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            fun logic(a: Boolean, b: Boolean) {
                if (a && b) {}
                if (a || b) {}
            }
        """,
        )
        # 1 (base) + 1 (if) + 1 (&&) + 1 (if) + 1 (||) = 5
        assert _find_function(r, "logic")["complexity"] == 5

    def test_try_catch(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            fun risky() {
                try {
                    dangerous()
                } catch (e: Exception) {
                    fallback()
                }
            }
        """,
        )
        # 1 (base) + 1 (catch) = 2
        assert _find_function(r, "risky")["complexity"] == 2


class TestStructures:
    def test_class_with_methods(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            class S {
                fun add(a: Int, b: Int): Int = a + b
                fun check(x: Int): Boolean {
                    if (x > 0) return true
                    return false
                }
            }
        """,
        )
        s = _find_class(r, "S")
        assert s["complexity"] == 3  # add(1) + check(2)
        assert len(s["methods"]) == 2

    def test_data_class(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            data class Point(val x: Int, val y: Int)
        """,
        )
        assert _find_class(r, "Point") is not None

    def test_object_declaration(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            object Config {
                val host = "localhost"
                fun url(): String = "http://$host"
            }
        """,
        )
        assert _find_class(r, "Config") is not None
        assert len(_find_class(r, "Config")["methods"]) == 1

    def test_interface(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            interface Service {
                fun execute()
            }
        """,
        )
        svc = _find_class(r, "Service")
        assert svc is not None

    def test_enum_class(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            enum class Color {
                RED, GREEN, BLUE
            }
        """,
        )
        c = _find_class(r, "Color")
        assert c is not None


class TestClosures:
    def test_lambda_closure(self, tmp_path):
        r = _single_kt(
            tmp_path,
            """\
            fun wrap() {
                val fn = { x: Int ->
                    if (x > 0) x else -x
                }
            }
        """,
        )
        w = _find_function(r, "wrap")
        assert w["complexity"] == 1
        assert len(w["closures"]) == 1
        assert w["closures"][0]["complexity"] == 2


class TestFiltering:
    def test_file_filtering(self, tmp_path):
        (tmp_path / "App.kt").write_text("fun main() {}\n")
        (tmp_path / "AppTest.kt").write_text("fun testApp() {}\n")

        build = tmp_path / "build"
        build.mkdir()
        (build / "Generated.kt").write_text("class Generated\n")

        r = collect(str(tmp_path))
        assert "App.kt" in r
        assert "AppTest.kt" not in r
        assert "build/Generated.kt" not in r
