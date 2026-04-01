"""Integration tests for Kotlin analyzer — runs real kotlinc -script on temp .kt files."""

import shutil
import textwrap

import pytest
from strictacode.kotlin.analyzer import analyze

pytestmark = pytest.mark.skipif(
    shutil.which("kotlinc") is None,
    reason="requires kotlinc",
)


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


class TestFiltering:
    def test_file_filtering(self, tmp_path):
        (tmp_path / "Main.kt").write_text("class Service\n")
        (tmp_path / "MainTest.kt").write_text("class ServiceTest\n")
        r = analyze(str(tmp_path))
        assert "Service" in _node_names(r)
        assert "ServiceTest" not in _node_names(r)
