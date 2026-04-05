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


class TestTypeUsage:
    """Tests for type usage edge detection."""

    def test_type_annotation_creates_usage_edge(self, tmp_path):
        """Property with declared type creates usage edge."""
        (tmp_path / "types.swift").write_text("class Request {}\nclass Handler {\n    var req: Request\n}\n")
        r = analyze(str(tmp_path))
        assert ("Handler", "Request") in _edge_pairs(r)

    def test_parameter_type_creates_usage_edge(self, tmp_path):
        """Method parameter type creates usage edge."""
        (tmp_path / "svc.swift").write_text("class Request {}\nclass Service {\n    func handle(_ r: Request) {}\n}\n")
        r = analyze(str(tmp_path))
        assert ("Service", "Request") in _edge_pairs(r)

    def test_return_type_creates_usage_edge(self, tmp_path):
        """Return type creates usage edge."""
        (tmp_path / "resp.swift").write_text(
            "class Response {}\nclass Client {\n    func fetch() -> Response { Response() }\n}\n"
        )
        r = analyze(str(tmp_path))
        assert ("Client", "Response") in _edge_pairs(r)

    def test_constructor_creates_usage_edge(self, tmp_path):
        """Constructor call creates usage edge."""
        (tmp_path / "err.swift").write_text(
            "class AFError {}\nclass Handler {\n    func fail() {\n        let e = AFError()\n    }\n}\n"
        )
        r = analyze(str(tmp_path))
        assert ("Handler", "AFError") in _edge_pairs(r)

    def test_no_self_usage_edge(self, tmp_path):
        """A type using itself does not create a self-edge."""
        (tmp_path / "self.swift").write_text("class Node {\n    var child: Node\n}\n")
        r = analyze(str(tmp_path))
        for e in r["edges"]:
            assert e["source"] != e["target"]

    def test_no_duplicate_usage_edge(self, tmp_path):
        """Multiple usages of same type create only one edge."""
        (tmp_path / "dup.swift").write_text(
            "class Request {}\n"
            "class Handler {\n"
            "    var a: Request\n"
            "    var b: Request\n"
            "    func make() -> Request { Request() }\n"
            "}\n"
        )
        r = analyze(str(tmp_path))
        handler_req = [e for e in r["edges"] if "Handler" in e["source"] and "Request" in e["target"]]
        assert len(handler_req) == 1

    def test_base_types_ignored(self, tmp_path):
        """Standard library types (String, Int, etc.) do not create edges."""
        (tmp_path / "base.swift").write_text(
            "class Config {\n    var name: String\n    var count: Int\n    var flag: Bool\n}\n"
        )
        r = analyze(str(tmp_path))
        assert r["edges"] == []

    def test_cross_file_usage(self, tmp_path):
        """Usage edge created when type is in a different file."""
        (tmp_path / "request.swift").write_text("class Request {}\n")
        (tmp_path / "handler.swift").write_text("class Handler {\n    func process(_ req: Request) {}\n}\n")
        r = analyze(str(tmp_path))
        assert ("Handler", "Request") in _edge_pairs(r)

    def test_usage_with_inheritance_combined(self, tmp_path):
        """Usage edges coexist with inheritance edges."""
        (tmp_path / "both.swift").write_text(
            "class Base {}\nclass Request {}\nclass Derived: Base {\n    var req: Request\n}\n"
        )
        r = analyze(str(tmp_path))
        pairs = _edge_pairs(r)
        assert ("Derived", "Base") in pairs
        assert ("Derived", "Request") in pairs

    def test_no_usage_edge_for_unknown_type(self, tmp_path):
        """Type not declared in project does not create an edge."""
        (tmp_path / "unk.swift").write_text("class Handler {\n    var logger: Logger\n}\n")
        r = analyze(str(tmp_path))
        assert r["edges"] == []


class TestTypeUsageAdditional:
    """Additional type usage edge tests for struct/enum/optional/nested."""

    def test_struct_usage_edge(self, tmp_path):
        """Struct with typed property creates usage edge."""
        (tmp_path / "model.swift").write_text("class Coordinate {}\nstruct Point {\n    var coord: Coordinate\n}\n")
        r = analyze(str(tmp_path))
        assert ("Point", "Coordinate") in _edge_pairs(r)

    def test_enum_usage_edge(self, tmp_path):
        """Enum with computed property creates usage edge."""
        (tmp_path / "result.swift").write_text(
            "class Logger {}\nenum Result {\n    case success\n    var log: Logger\n}\n"
        )
        r = analyze(str(tmp_path))
        assert ("Result", "Logger") in _edge_pairs(r)

    def test_optional_type_usage_edge(self, tmp_path):
        """Optional type annotation Request? creates usage edge."""
        (tmp_path / "opt.swift").write_text("class Request {}\nclass Handler {\n    var req: Request?\n}\n")
        r = analyze(str(tmp_path))
        assert ("Handler", "Request") in _edge_pairs(r)

    def test_nested_type_usage_edge(self, tmp_path):
        """Nested type using another type creates usage edge."""
        (tmp_path / "nested.swift").write_text(
            "class Config {}\nclass Container {\n    class Item {\n        var cfg: Config\n    }\n}\n"
        )
        r = analyze(str(tmp_path))
        assert ("Container.Item", "Config") in _edge_pairs(r)

    def test_usage_edge_no_duplicate_with_inheritance(self, tmp_path):
        """Same type used in property AND inherited does not create duplicate."""
        (tmp_path / "both.swift").write_text(
            "class Base {}\nclass Service {}\nclass Client: Base {\n    var svc: Service\n}\n"
        )
        r = analyze(str(tmp_path))
        pairs = _edge_pairs(r)
        assert ("Client", "Base") in pairs
        assert ("Client", "Service") in pairs
        client_svc = [e for e in r["edges"] if "Client" in e["source"] and "Service" in e["target"]]
        assert len(client_svc) == 1


class TestFiltering:
    def test_file_filtering(self, tmp_path):
        (tmp_path / "Service.swift").write_text("class Service {}\n")
        (tmp_path / "ServiceTest.swift").write_text("class ServiceTest {}\n")
        r = analyze(str(tmp_path))
        assert "Service" in _node_names(r)
        assert "ServiceTest" not in _node_names(r)
