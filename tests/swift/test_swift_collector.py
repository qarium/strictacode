import textwrap

from strictacode.swift.collector import collect


def _write_swift(tmp_path, name, code):
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "Main.swift").write_text(textwrap.dedent(code))
    return collect(str(d))


def _single_swift(tmp_path, code):
    return _write_swift(tmp_path, "pkg", code)


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
    def test_empty_function(self, tmp_path):
        r = _single_swift(tmp_path, "func f() -> Int { return 42 }\n")
        assert _find_function(r, "f")["complexity"] == 1

    def test_single_if(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func g(x: Int) -> Int {
                if x > 0 { return x }
                return -1
            }
        """,
        )
        assert _find_function(r, "g")["complexity"] == 2

    def test_guard(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func check(x: Int?) -> Int {
                guard let val = x else { return 0 }
                return val
            }
        """,
        )
        assert _find_function(r, "check")["complexity"] == 2

    def test_for_loop(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func loop(items: [Int]) {
                for item in items {}
            }
        """,
        )
        assert _find_function(r, "loop")["complexity"] == 2

    def test_switch_case(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func sw(x: Int) -> String {
                switch x {
                case 1: return "one"
                case 2: return "two"
                default: return "other"
                }
            }
        """,
        )
        # 1 (base) + 2 (case branches) + 1 (default) = 4
        assert _find_function(r, "sw")["complexity"] == 4

    def test_logical_and_or(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func logic(a: Bool, b: Bool) {
                if a && b {}
                if a || b {}
            }
        """,
        )
        # 1 (base) + 1 (if) + 1 (&&) + 1 (if) + 1 (||) = 5
        assert _find_function(r, "logic")["complexity"] == 5

    def test_catch(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func risky() {
                do {
                    try dangerous()
                } catch {
                    fallback()
                }
            }
        """,
        )
        # 1 (base) + 1 (catch) = 2
        assert _find_function(r, "risky")["complexity"] == 2


class TestStructures:
    def test_struct_with_methods(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            struct Point {
                var x: Int
                var y: Int
                func add(p: Point) -> Point {
                    return Point(x: x + p.x, y: y + p.y)
                }
            }
        """,
        )
        s = _find_class(r, "Point")
        assert len(s["methods"]) == 1
        assert s["methods"][0]["name"] == "add"

    def test_class_with_methods(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            class Service {
                func execute() -> Bool {
                    if true { return true }
                    return false
                }
            }
        """,
        )
        s = _find_class(r, "Service")
        assert s["complexity"] == 2
        assert len(s["methods"]) == 1

    def test_enum(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            enum Color {
                case red, green, blue
            }
        """,
        )
        assert _find_class(r, "Color") is not None

    def test_protocol(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            protocol Drawable {
                func draw()
            }
        """,
        )
        assert _find_class(r, "Drawable") is not None

    def test_actor(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            actor Counter {
                var value = 0
                func increment() -> Int {
                    value += 1
                    return value
                }
            }
        """,
        )
        assert _find_class(r, "Counter") is not None

    def test_extension(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            extension String {
                var trimmed: String {
                    return self
                }
            }
        """,
        )
        assert _find_class(r, "String") is not None

    def test_static_func(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            class Factory {
                static func create() -> Factory {
                    return Factory()
                }
            }
        """,
        )
        s = _find_class(r, "Factory")
        assert len(s["methods"]) == 1
        assert s["methods"][0]["name"] == "create"


class TestClosures:
    def test_named_closure(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func wrap() {
                let fn = { (x: Int) -> Int in
                    if x > 0 { return x }
                    return -x
                }
            }
        """,
        )
        w = _find_function(r, "wrap")
        assert w["complexity"] == 1
        assert len(w["closures"]) == 1
        assert w["closures"][0]["complexity"] == 2


class TestWhileLoops:
    def test_while_statement(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func wait(x: Int) {
                while x > 0 {}
            }
        """,
        )
        assert _find_function(r, "wait")["complexity"] == 2

    def test_repeat_while(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func repeatFunc(x: Int) {
                repeat {} while x > 0
            }
        """,
        )
        assert _find_function(r, "repeatFunc")["complexity"] == 2


class TestTernaryComplexity:
    def test_ternary_not_counted(self, tmp_path):
        """Ternary expressions are not decision nodes in McCabe complexity."""
        r = _single_swift(
            tmp_path,
            """\
            func check(x: Int) -> Int {
                let y = x > 0 ? x : -x
                return y
            }
        """,
        )
        assert _find_function(r, "check")["complexity"] == 1


class TestNestedClosures:
    def test_nested_closure_complexity(self, tmp_path):
        r = _single_swift(
            tmp_path,
            """\
            func outer() {
                let fn = { (x: Int) -> Int in
                    let inner = { (y: Int) -> Int in
                        if y > 0 { return y }
                        return -y
                    }
                    return inner(x)
                }
            }
        """,
        )
        w = _find_function(r, "outer")
        assert len(w["closures"]) >= 1


class TestFiltering:
    def test_file_filtering(self, tmp_path):
        (tmp_path / "App.swift").write_text("func main() {}\n")
        (tmp_path / "AppTest.swift").write_text("func testApp() {}\n")

        build = tmp_path / ".build"
        build.mkdir()
        (build / "Generated.swift").write_text("class Generated {}\n")

        r = collect(str(tmp_path))
        filenames = list(r.keys())
        assert any("App.swift" in f for f in filenames)
        assert not any("AppTest.swift" in f for f in filenames)
        assert not any("Generated.swift" in f for f in filenames)
