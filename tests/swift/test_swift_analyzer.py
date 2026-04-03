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
            tmp_path, "inherit.swift",
            """\
            class Base {}
            class Derived: Base {}
        """,
        )
        assert ("Derived", "Base") in _edge_pairs(r)

    def test_class_conforms_protocol(self, tmp_path):
        r = _write(
            tmp_path, "conform.swift",
            """\
            protocol Service {}
            class ServiceImpl: Service {}
        """,
        )
        assert ("ServiceImpl", "Service") in _edge_pairs(r)

    def test_struct_conforms_protocol(self, tmp_path):
        r = _write(
            tmp_path, "struct_proto.swift",
            """\
            protocol Drawable {}
            struct Circle: Drawable {}
        """,
        )
        assert ("Circle", "Drawable") in _edge_pairs(r)

    def test_multiple_conformance(self, tmp_path):
        r = _write(
            tmp_path, "multi.swift",
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
            tmp_path, "proto_ext.swift",
            """\
            protocol Readable {}
            protocol Writable: Readable {}
        """,
        )
        assert ("Writable", "Readable") in _edge_pairs(r)

    def test_actor_conforms(self, tmp_path):
        r = _write(
            tmp_path, "actor_conf.swift",
            """\
            protocol Lockable {}
            actor Mutex: Lockable {}
        """,
        )
        assert ("Mutex", "Lockable") in _edge_pairs(r)

    def test_extension_conforms(self, tmp_path):
        r = _write(
            tmp_path, "ext_conf.swift",
            """\
            protocol Serializable {}
            extension Data: Serializable {}
        """,
        )
        assert ("Data", "Serializable") in _edge_pairs(r)


class TestFiltering:
    def test_file_filtering(self, tmp_path):
        (tmp_path / "Service.swift").write_text("class Service {}\n")
        (tmp_path / "ServiceTest.swift").write_text("class ServiceTest {}\n")
        r = analyze(str(tmp_path))
        assert "Service" in _node_names(r)
        assert "ServiceTest" not in _node_names(r)
