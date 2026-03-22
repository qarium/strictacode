"""Integration tests for Go analyzer — runs real `go run` on temp .go files."""

import shutil
import textwrap

import pytest
from strictacode.go.analyzer import analyze

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


def _write(tmp_path, filename, code):
    (tmp_path / filename).write_text(textwrap.dedent(code))
    return analyze(str(tmp_path))


def _node_names(result):
    return {n.split(":")[-1] for n in result["nodes"]}


def _edge_pairs(result):
    return {(e["source"].split(":")[-1], e["target"].split(":")[-1]) for e in result["edges"]}


# ===========================================================================
# Node tests
# ===========================================================================


class TestNodes:
    def test_struct_node(self, tmp_path):
        r = _write(
            tmp_path,
            "types.go",
            """\
            package main
            type User struct {}
        """,
        )
        assert "User" in _node_names(r)

    def test_interface_node(self, tmp_path):
        r = _write(
            tmp_path,
            "iface.go",
            """\
            package main
            type Writer interface {}
        """,
        )
        assert "Writer" in _node_names(r)


# ===========================================================================
# Embedded type edges
# ===========================================================================


class TestEmbeddedEdges:
    def test_embedded_type(self, tmp_path):
        r = _write(
            tmp_path,
            "embed.go",
            """\
            package main
            type Base struct {}
            type Extended struct { Base }
        """,
        )
        assert ("Extended", "Base") in _edge_pairs(r)

    def test_pointer_embedded(self, tmp_path):
        r = _write(
            tmp_path,
            "ptr_embed.go",
            """\
            package main
            type Base struct {}
            type Derived struct { *Base }
        """,
        )
        assert ("Derived", "Base") in _edge_pairs(r)


# ===========================================================================
# Interface implementation edges
# ===========================================================================


class TestInterfaceImplementation:
    def test_interface_impl(self, tmp_path):
        r = _write(
            tmp_path,
            "impl.go",
            """\
            package main
            type Greeter interface { Greet() }
            type Hello struct{}
            func (h Hello) Greet() {}
        """,
        )
        assert ("Hello", "Greeter") in _edge_pairs(r)

    def test_no_interface_impl(self, tmp_path):
        r = _write(
            tmp_path,
            "no_impl.go",
            """\
            package main
            type Greeter interface { Greet(name string) }
            type Hello struct{}
            func (h Hello) Greet() {}
        """,
        )
        assert ("Hello", "Greeter") not in _edge_pairs(r)

    def test_multi_impl(self, tmp_path):
        r = _write(
            tmp_path,
            "multi.go",
            """\
            package main
            type Reader interface { Read() }
            type Writer interface { Write() }
            type File struct{}
            func (f File) Read() {}
            func (f File) Write() {}
        """,
        )
        pairs = _edge_pairs(r)
        assert ("File", "Reader") in pairs
        assert ("File", "Writer") in pairs

    def test_embedded_interface(self, tmp_path):
        r = _write(
            tmp_path,
            "rw.go",
            """\
            package main
            type ReadWriter interface { Read(); Write() }
            type ReadWriteCloser interface { ReadWriter; Close() }
        """,
        )
        assert ("ReadWriteCloser", "ReadWriter") in _edge_pairs(r)

    def test_selector_embedded(self, tmp_path):
        r = _write(
            tmp_path,
            "fmt_embed.go",
            """\
            package main
            import "fmt"
            type MyWriter struct { fmt.Stringer }
        """,
        )
        assert ("MyWriter", "Stringer") in _edge_pairs(r)


# ===========================================================================
# Other tests
# ===========================================================================


class TestOther:
    def test_empty_struct(self, tmp_path):
        r = _write(
            tmp_path,
            "empty.go",
            """\
            package main
            type NoMethods struct {}
        """,
        )
        assert "NoMethods" in _node_names(r)
        assert len(r["edges"]) == 0

    def test_file_filtering(self, tmp_path):
        """vendor/ and _test.go are excluded."""
        (tmp_path / "main.go").write_text(
            textwrap.dedent("""\
            package main
            type Service struct {}
        """)
        )
        (tmp_path / "main_test.go").write_text(
            textwrap.dedent("""\
            package main
            func TestService() {}
        """)
        )
        vendor = tmp_path / "vendor"
        vendor.mkdir()
        (vendor / "dep.go").write_text(
            textwrap.dedent("""\
            package vendor
            type Dep struct {}
        """)
        )
        r = analyze(str(tmp_path))
        assert "Service" in _node_names(r)
        # vendor/dep.go and main_test.go should be excluded
        assert "Dep" not in _node_names(r)
