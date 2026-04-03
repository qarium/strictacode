import textwrap

from strictacode.swift.analyzer import analyze


def _write(tmp_path, filename, code):
    (tmp_path / filename).write_text(textwrap.dedent(code))
    return analyze(str(tmp_path))


def _node_names(result):
    return {n.split(":")[-1] for n in result["nodes"]}


def _edge_pairs(result):
    return {(e["source"].split(":")[-1], e["target"].split(":")[-1]) for e in result["edges"]}


class TestNodes:
    def test_struct_node(self, tmp_path):
        r = _write(tmp_path, "types.swift", "struct Point {}\n")
        assert "Point" in _node_names(r)

    def test_class_node(self, tmp_path):
        r = _write(tmp_path, "cls.swift", "class User {}\n")
        assert "User" in _node_names(r)

    def test_enum_node(self, tmp_path):
        r = _write(tmp_path, "en.swift", "enum Color {}\n")
        assert "Color" in _node_names(r)

    def test_protocol_node(self, tmp_path):
        r = _write(tmp_path, "proto.swift", "protocol Drawable {}\n")
        assert "Drawable" in _node_names(r)

    def test_actor_node(self, tmp_path):
        r = _write(tmp_path, "act.swift", "actor Counter {}\n")
        assert "Counter" in _node_names(r)

    def test_extension_node(self, tmp_path):
        r = _write(tmp_path, "ext.swift", "extension String {}\n")
        assert "String" in _node_names(r)


class TestInheritance:
    def test_class_inherits(self, tmp_path):
        r = _write(
            tmp_path,
            "inherit.swift",
            """\
            class Base {}
            class Derived: Base {}
        """,
        )
        assert ("Derived", "Base") in _edge_pairs(r)

    def test_class_conforms_protocol(self, tmp_path):
        r = _write(
            tmp_path,
            "conform.swift",
            """\
            protocol Service {}
            class ServiceImpl: Service {}
        """,
        )
        assert ("ServiceImpl", "Service") in _edge_pairs(r)

    def test_struct_conforms_protocol(self, tmp_path):
        r = _write(
            tmp_path,
            "struct_proto.swift",
            """\
            protocol Drawable {}
            struct Circle: Drawable {}
        """,
        )
        assert ("Circle", "Drawable") in _edge_pairs(r)

    def test_multiple_conformance(self, tmp_path):
        r = _write(
            tmp_path,
            "multi.swift",
            """\
            class Base {}
            protocol Readable {}
            protocol Writable {}
            class File: Base, Readable, Writable {}
        """,
        )
        pairs = _edge_pairs(r)
        assert ("File", "Base") in pairs
        assert ("File", "Readable") in pairs
        assert ("File", "Writable") in pairs

    def test_protocol_inherits(self, tmp_path):
        r = _write(
            tmp_path,
            "proto_ext.swift",
            """\
            protocol Readable {}
            protocol Writable: Readable {}
        """,
        )
        assert ("Writable", "Readable") in _edge_pairs(r)

    def test_actor_conforms(self, tmp_path):
        r = _write(
            tmp_path,
            "actor_conf.swift",
            """\
            protocol Lockable {}
            actor Mutex: Lockable {}
        """,
        )
        assert ("Mutex", "Lockable") in _edge_pairs(r)

    def test_extension_conforms(self, tmp_path):
        r = _write(
            tmp_path,
            "ext_conf.swift",
            """\
            protocol Serializable {}
            extension Data: Serializable {}
        """,
        )
        assert ("Data", "Serializable") in _edge_pairs(r)


class TestTwoPassResolution:
    """Tests for the two-pass name resolution fix."""

    def test_child_before_parent_different_files(self, tmp_path):
        """Edge preserved when child file is processed before parent file."""
        (tmp_path / "a_Impl.swift").write_text("class ServiceImpl: Service {}\n")
        (tmp_path / "b_Base.swift").write_text("class Service {}\n")
        r = analyze(str(tmp_path))
        assert ("ServiceImpl", "Service") in _edge_pairs(r)

    def test_cross_file_inheritance(self, tmp_path):
        """Edge created when parent is in a different file."""
        (tmp_path / "base.swift").write_text("class Repository {}\n")
        (tmp_path / "impl.swift").write_text("class UserRepo: Repository {}\n")
        r = analyze(str(tmp_path))
        assert ("UserRepo", "Repository") in _edge_pairs(r)

    def test_external_dependency_not_linked(self, tmp_path):
        """Edges to types not declared in project are not created."""
        (tmp_path / "svc.swift").write_text("class MyView: UIView {}\n")
        r = analyze(str(tmp_path))
        assert len(r["edges"]) == 0

    def test_no_self_edge(self, tmp_path):
        """A type does not get an edge to itself."""
        (tmp_path / "a.swift").write_text("class Base {}\n")
        r = analyze(str(tmp_path))
        for e in r["edges"]:
            assert e["source"] != e["target"]


class TestNestedTypes:
    """Tests for nested type extraction."""

    def test_nested_class_detected(self, tmp_path):
        """Nested class inside another class is detected."""
        r = _write(
            tmp_path,
            "outer.swift",
            "class Outer {\n    class Inner {}\n}\n",
        )
        names = _node_names(r)
        assert "Outer" in names
        assert "Outer.Inner" in names

    def test_nested_class_inherits(self, tmp_path):
        """Nested class inheriting from top-level type gets an edge."""
        r = _write(
            tmp_path,
            "nested.swift",
            "class Base {}\nclass Container {\n    class Item: Base {}\n}\n",
        )
        assert ("Container.Item", "Base") in _edge_pairs(r)

    def test_nested_protocol_detected(self, tmp_path):
        """Nested protocol inside a class is detected."""
        r = _write(
            tmp_path,
            "nested_proto.swift",
            "class Factory {\n    protocol Product {}\n}\n",
        )
        assert "Factory.Product" in _node_names(r)


class TestProtocolConformance:
    """Tests for implicit protocol conformance detection via method signatures."""

    def test_implicit_conformance(self, tmp_path):
        """Class with all protocol methods gets an implicit edge."""
        (tmp_path / "proto.swift").write_text("protocol Drawable {\n    func draw()\n    func resize(scale: Int)\n}\n")
        (tmp_path / "impl.swift").write_text("class Circle {\n    func draw() {}\n    func resize(scale: Int) {}\n}\n")
        r = analyze(str(tmp_path))
        assert ("Circle", "Drawable") in _edge_pairs(r)

    def test_no_match_when_method_missing(self, tmp_path):
        """No implicit edge when class is missing a protocol method."""
        (tmp_path / "proto.swift").write_text("protocol Drawable {\n    func draw()\n    func resize(scale: Int)\n}\n")
        (tmp_path / "impl.swift").write_text("class Circle {\n    func draw() {}\n}\n")
        r = analyze(str(tmp_path))
        assert ("Circle", "Drawable") not in _edge_pairs(r)

    def test_explicit_edge_not_duplicated(self, tmp_path):
        """Explicit conformance edge is not duplicated."""
        (tmp_path / "proto.swift").write_text("protocol Handler {\n    func handle()\n}\n")
        (tmp_path / "impl.swift").write_text("class HttpHandler: Handler {\n    func handle() {}\n}\n")
        r = analyze(str(tmp_path))
        handler_edges = [e for e in r["edges"] if "HttpHandler" in e["source"]]
        assert len(handler_edges) == 1

    def test_empty_protocol_no_false_edges(self, tmp_path):
        """An empty protocol doesn't create edges to everything."""
        (tmp_path / "proto.swift").write_text("protocol Empty {}\n")
        (tmp_path / "cls.swift").write_text("class MyClass {\n    func doWork() {}\n}\n")
        r = analyze(str(tmp_path))
        assert ("MyClass", "Empty") not in _edge_pairs(r)


class TestEmptyDirectory:
    def test_empty_dir_returns_empty(self, tmp_path):
        r = analyze(str(tmp_path))
        assert r["nodes"] == []
        assert r["edges"] == []

    def test_dir_with_no_swift_files(self, tmp_path):
        (tmp_path / "readme.txt").write_text("not swift")
        r = analyze(str(tmp_path))
        assert r["nodes"] == []
        assert r["edges"] == []


class TestCircularInheritance:
    def test_no_crash_on_circular_inheritance(self, tmp_path):
        """Circular inheritance should not cause infinite loops or crashes."""
        (tmp_path / "a.swift").write_text("protocol A: B {}\nprotocol B: A {}\n")
        r = analyze(str(tmp_path))
        names = _node_names(r)
        assert "A" in names
        assert "B" in names


class TestFiltering:
    def test_file_filtering(self, tmp_path):
        (tmp_path / "Service.swift").write_text("class Service {}\n")
        (tmp_path / "ServiceTest.swift").write_text("class ServiceTest {}\n")
        r = analyze(str(tmp_path))
        assert "Service" in _node_names(r)
        assert "ServiceTest" not in _node_names(r)
