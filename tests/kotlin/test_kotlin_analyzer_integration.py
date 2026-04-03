"""Integration tests for Kotlin analyzer — pure Python + tree-sitter."""

import textwrap

from strictacode.kotlin.analyzer import analyze


def _write(tmp_path, filename, code):
    (tmp_path / filename).write_text(textwrap.dedent(code))
    return analyze(str(tmp_path))


def _node_names(result):
    return {n.split(":")[-1] for n in result["nodes"]}


def _edge_pairs(result):
    return {(e["source"].split(":")[-1], e["target"].split(":")[-1]) for e in result["edges"]}


class TestNodes:
    def test_class_node(self, tmp_path):
        r = _write(tmp_path, "types.kt", "class User\n")
        assert "User" in _node_names(r)

    def test_interface_node(self, tmp_path):
        r = _write(tmp_path, "iface.kt", "interface Writer\n")
        assert "Writer" in _node_names(r)

    def test_object_node(self, tmp_path):
        r = _write(tmp_path, "obj.kt", "object Config\n")
        assert "Config" in _node_names(r)


class TestInheritance:
    def test_class_extends(self, tmp_path):
        r = _write(
            tmp_path,
            "inherit.kt",
            """\
            open class Base
            class Derived : Base()
        """,
        )
        assert ("Derived", "Base") in _edge_pairs(r)

    def test_class_implements_interface(self, tmp_path):
        r = _write(
            tmp_path,
            "impl.kt",
            """\
            interface Service
            class ServiceImpl : Service
        """,
        )
        assert ("ServiceImpl", "Service") in _edge_pairs(r)

    def test_class_extends_and_implements(self, tmp_path):
        r = _write(
            tmp_path,
            "multi.kt",
            """\
            open class Base
            interface Readable
            interface Writable
            class File : Base(), Readable, Writable
        """,
        )
        pairs = _edge_pairs(r)
        assert ("File", "Base") in pairs
        assert ("File", "Readable") in pairs
        assert ("File", "Writable") in pairs

    def test_interface_extends(self, tmp_path):
        r = _write(
            tmp_path,
            "iface_ext.kt",
            """\
            interface Readable
            interface Writable : Readable
        """,
        )
        assert ("Writable", "Readable") in _edge_pairs(r)

    def test_object_implements(self, tmp_path):
        r = _write(
            tmp_path,
            "obj_impl.kt",
            """\
            interface Singleton
            object Database : Singleton
        """,
        )
        assert ("Database", "Singleton") in _edge_pairs(r)


class TestTwoPassResolution:
    """Tests for the two-pass name resolution fix.

    Previously the analyzer used a single-pass algorithm where name_to_file
    was built incrementally. If a child class was processed before its parent,
    the edge was lost because the parent name was not yet known.
    """

    def test_child_before_parent_different_files(self, tmp_path):
        """Edge preserved when child file is processed before parent file."""
        (tmp_path / "a_Service.kt").write_text("class ServiceImpl : Service\n")
        (tmp_path / "b_Base.kt").write_text("open class Service\n")
        r = analyze(str(tmp_path))
        assert ("ServiceImpl", "Service") in _edge_pairs(r)

    def test_duplicate_class_name_different_files(self, tmp_path):
        """Edge targets the correct file when class name appears in multiple files."""
        pkg1 = tmp_path / "pkg1"
        pkg2 = tmp_path / "pkg2"
        pkg1.mkdir()
        pkg2.mkdir()
        (pkg1 / "a.kt").write_text("open class Base\n")
        (pkg2 / "a.kt").write_text("open class Base\n")
        (pkg1 / "child.kt").write_text("class Child : Base()\n")
        r = analyze(str(tmp_path))
        assert ("Child", "Base") in _edge_pairs(r)

    def test_same_file_preference_for_duplicate_names(self, tmp_path):
        """When duplicate names exist, same-file match is preferred."""
        (tmp_path / "a.kt").write_text("open class Handler\n")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.kt").write_text("open class Handler\nclass SubHandler : Handler()\n")
        r = analyze(str(tmp_path))
        # SubHandler should connect to sub/b.kt:Handler (same file)
        edges = r["edges"]
        sub_edges = [e for e in edges if "SubHandler" in e["source"]]
        assert len(sub_edges) == 1
        assert "sub/b.kt" in sub_edges[0]["target"]

    def test_cross_file_inheritance(self, tmp_path):
        """Edge created when parent is in a different file."""
        (tmp_path / "base.kt").write_text("open class Repository\n")
        (tmp_path / "impl.kt").write_text("class UserRepository : Repository()\n")
        r = analyze(str(tmp_path))
        assert ("UserRepository", "Repository") in _edge_pairs(r)

    def test_external_dependency_not_linked(self, tmp_path):
        """Edges to types not declared in project are not created."""
        (tmp_path / "svc.kt").write_text("class MyService : ExternalLib()\n")
        r = analyze(str(tmp_path))
        assert len(r["edges"]) == 0

    def test_no_self_edge(self, tmp_path):
        """A type does not get an edge to itself."""
        (tmp_path / "a.kt").write_text("open class Base\n")
        r = analyze(str(tmp_path))
        for e in r["edges"]:
            assert e["source"] != e["target"]


class TestInterfaceMatching:
    """Tests for implicit interface implementation detection via method signatures.

    Similar to Go's checkInterfaceImplementation, the analyzer detects when a
    class implements all methods of an interface and adds an implicit edge.
    """

    def test_implicit_interface_match(self, tmp_path):
        """Class with all interface methods gets an implicit edge."""
        (tmp_path / "iface.kt").write_text("interface Drawable {\n    fun draw()\n    fun resize(scale: Int)\n}\n")
        (tmp_path / "impl.kt").write_text(
            "class Circle : Drawable {\n    override fun draw() {}\n    override fun resize(scale: Int) {}\n}\n"
        )
        r = analyze(str(tmp_path))
        assert ("Circle", "Drawable") in _edge_pairs(r)

    def test_no_match_when_method_missing(self, tmp_path):
        """No implicit edge when class is missing an interface method."""
        (tmp_path / "iface.kt").write_text("interface Drawable {\n    fun draw()\n    fun resize(scale: Int)\n}\n")
        (tmp_path / "impl.kt").write_text("class Circle {\n    fun draw() {}\n}\n")
        r = analyze(str(tmp_path))
        assert ("Circle", "Drawable") not in _edge_pairs(r)

    def test_explicit_edge_not_duplicated(self, tmp_path):
        """Explicit inheritance edge is not duplicated by interface matching."""
        (tmp_path / "iface.kt").write_text("interface Handler {\n    fun handle()\n}\n")
        (tmp_path / "impl.kt").write_text("class HttpHandler : Handler {\n    override fun handle() {}\n}\n")
        r = analyze(str(tmp_path))
        edges_to_handler = [e for e in r["edges"] if "HttpHandler" in e["source"]]
        assert len(edges_to_handler) == 1

    def test_object_implements_interface_implicitly(self, tmp_path):
        """Object declarations are also matched against interfaces."""
        (tmp_path / "iface.kt").write_text("interface Serializer {\n    fun serialize(data: String): ByteArray\n}\n")
        (tmp_path / "obj.kt").write_text(
            "object JsonSerializer {\n    fun serialize(data: String): ByteArray = ByteArray(0)\n}\n"
        )
        r = analyze(str(tmp_path))
        assert ("JsonSerializer", "Serializer") in _edge_pairs(r)

    def test_empty_interface_no_false_edges(self, tmp_path):
        """An interface with no methods doesn't create edges to everything."""
        (tmp_path / "iface.kt").write_text("interface Empty\n")
        (tmp_path / "cls.kt").write_text("class MyClass {\n    fun doWork() {}\n}\n")
        r = analyze(str(tmp_path))
        assert ("MyClass", "Empty") not in _edge_pairs(r)


class TestNestedClasses:
    """Tests for nested class extraction.

    Kotlin allows classes inside other classes. Previously the analyzer only
    scanned top-level declarations, missing nested types and their inheritance
    relationships.
    """

    def test_nested_class_detected(self, tmp_path):
        """Nested class inside another class is detected as a node."""
        r = _write(
            tmp_path,
            "outer.kt",
            """\
            class Outer {
                class Inner
            }
            """,
        )
        names = _node_names(r)
        assert "Outer" in names
        assert "Outer.Inner" in names

    def test_nested_object_detected(self, tmp_path):
        """Nested object inside a class is detected."""
        r = _write(
            tmp_path,
            "obj.kt",
            """\
            class Config {
                object Defaults
            }
            """,
        )
        names = _node_names(r)
        assert "Config.Defaults" in names

    def test_nested_class_inherits_parent(self, tmp_path):
        """Nested class inheriting from top-level type gets an edge."""
        r = _write(
            tmp_path,
            "nested.kt",
            """\
            open class Base
            class Outer {
                class Inner : Base()
            }
            """,
        )
        assert ("Outer.Inner", "Base") in _edge_pairs(r)

    def test_nested_class_inherits_nested(self, tmp_path):
        """Nested class inheriting from another nested type in same file."""
        r = _write(
            tmp_path,
            "both.kt",
            """\
            class Container {
                open class A
                class B : A()
            }
            """,
        )
        assert ("Container.B", "Container.A") in _edge_pairs(r)

    def test_deeply_nested_class(self, tmp_path):
        """Two levels of nesting are detected."""
        r = _write(
            tmp_path,
            "deep.kt",
            """\
            class Level1 {
                class Level2 {
                    class Level3
                }
            }
            """,
        )
        names = _node_names(r)
        assert "Level1.Level2.Level3" in names

    def test_nested_in_cross_file(self, tmp_path):
        """Nested class can inherit from a type in a different file."""
        (tmp_path / "base.kt").write_text("open class Plugin\n")
        (tmp_path / "impl.kt").write_text("class Registry {\n    class MyPlugin : Plugin()\n}\n")
        r = analyze(str(tmp_path))
        assert ("Registry.MyPlugin", "Plugin") in _edge_pairs(r)

    def test_function_body_not_scanned(self, tmp_path):
        """Classes inside function bodies are not detected (runtime types)."""
        r = _write(
            tmp_path,
            "local.kt",
            """\
            class Outer {
                fun factory() {
                    class LocalHelper
                }
            }
            """,
        )
        names = _node_names(r)
        assert "Outer" in names
        assert "LocalHelper" not in names


class TestExplicitDelegation:
    """Tests for explicit delegation (``by`` keyword) edge extraction.

    Kotlin's ``class X : Interface by delegate`` creates a relationship
    to Interface that must be captured.
    """

    def test_by_delegate_creates_edge(self, tmp_path):
        """Interface in explicit_delegation is extracted as super."""
        r = _write(
            tmp_path,
            "delegate.kt",
            """\
            interface Socket {
                fun close()
            }
            class BufferedSocket : Socket by rawSocket {
                val rawSocket = object : Socket {
                    override fun close() {}
                }
            }
            """,
        )
        assert ("BufferedSocket", "Socket") in _edge_pairs(r)

    def test_by_with_constructor_extends(self, tmp_path):
        """``class X : Base(), Interface by impl`` — both edges captured."""
        r = _write(
            tmp_path,
            "mixed.kt",
            """\
            open class Base
            interface Plugin {
                fun install()
            }
            class App : Base(), Plugin by defaultPlugin {
                companion object {
                    val defaultPlugin = object : Plugin {
                        override fun install() {}
                    }
                }
            }
            """,
        )
        pairs = _edge_pairs(r)
        assert ("App", "Base") in pairs
        assert ("App", "Plugin") in pairs

    def test_by_reference_to_project_type(self, tmp_path):
        """Delegated interface resolved when defined in another file."""
        (tmp_path / "repo.kt").write_text("interface Repository {\n    fun find(id: Int): String\n}\n")
        (tmp_path / "cached.kt").write_text(
            "class CachedRepo : Repository by delegate {\n"
            "    val delegate = object : Repository {\n"
            '        override fun find(id: Int) = ""\n'
            "    }\n"
            "}\n"
        )
        r = analyze(str(tmp_path))
        assert ("CachedRepo", "Repository") in _edge_pairs(r)


class TestEmptyDirectory:
    def test_empty_dir_returns_empty(self, tmp_path):
        r = analyze(str(tmp_path))
        assert r["nodes"] == []
        assert r["edges"] == []

    def test_dir_with_no_kotlin_files(self, tmp_path):
        (tmp_path / "readme.txt").write_text("not kotlin")
        r = analyze(str(tmp_path))
        assert r["nodes"] == []
        assert r["edges"] == []


class TestFiltering:
    def test_file_filtering(self, tmp_path):
        (tmp_path / "Main.kt").write_text("class Service\n")
        (tmp_path / "MainTest.kt").write_text("class ServiceTest\n")
        r = analyze(str(tmp_path))
        assert "Service" in _node_names(r)
        assert "ServiceTest" not in _node_names(r)
