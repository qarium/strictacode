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


# ===========================================================================
# Type Usage tests
# ===========================================================================


class TestTypeUsage:
    def test_struct_field_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "fields.go",
            """\
            package main
            type Request struct {}
            type Response struct {}
            type Handler struct {
                req Request
                resp *Response
            }
        """,
        )
        pairs = _edge_pairs(r)
        assert ("Handler", "Request") in pairs
        assert ("Handler", "Response") in pairs

    def test_method_param_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "params.go",
            """\
            package main
            type Input struct {}
            type Output struct {}
            type Worker struct {}
            func (w Worker) Run(in Input) Output { return Output{} }
        """,
        )
        pairs = _edge_pairs(r)
        assert ("Worker", "Input") in pairs
        assert ("Worker", "Output") in pairs

    def test_var_declaration_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "vars.go",
            """\
            package main
            type Config struct {}
            type Service struct {}
            func (s Service) Load() {
                var cfg Config
                _ = cfg
            }
        """,
        )
        pairs = _edge_pairs(r)
        assert ("Service", "Config") in pairs

    def test_composite_literal_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "comp.go",
            """\
            package main
            type Result struct {}
            type Builder struct {}
            func (b Builder) Build() {
                r := Result{}
                _ = r
            }
        """,
        )
        pairs = _edge_pairs(r)
        assert ("Builder", "Result") in pairs

    def test_no_base_type_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "basic.go",
            """\
            package main
            type Holder struct {
                name string
                age  int
                flag bool
            }
        """,
        )
        assert len(r["edges"]) == 0

    def test_no_self_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "self.go",
            """\
            package main
            type Node struct {
                children []Node
            }
        """,
        )
        assert len(r["edges"]) == 0

    def test_pointer_field_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "ptr.go",
            """\
            package main
            type Inner struct {}
            type Outer struct {
                inner *Inner
            }
        """,
        )
        assert ("Outer", "Inner") in _edge_pairs(r)

    def test_cross_file_usage(self, tmp_path):
        (tmp_path / "models.go").write_text(
            textwrap.dedent("""\
            package main
            type Request struct {}
            type Response struct {}
        """)
        )
        (tmp_path / "handler.go").write_text(
            textwrap.dedent("""\
            package main
            type Handler struct {
                req Request
            }
            func (h Handler) Process() Response {
                return Response{}
            }
        """)
        )
        r = analyze(str(tmp_path))
        pairs = _edge_pairs(r)
        assert ("Handler", "Request") in pairs
        assert ("Handler", "Response") in pairs

    def test_embedded_and_usage_combined(self, tmp_path):
        """Embedded (inheritance) + named field (usage) are both detected."""
        r = _write(
            tmp_path,
            "both.go",
            """\
            package main
            type Base struct {}
            type Extra struct {}
            type Child struct {
                Base
                ext Extra
            }
        """,
        )
        pairs = _edge_pairs(r)
        assert ("Child", "Base") in pairs
        assert ("Child", "Extra") in pairs

    def test_new_expression_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "new_expr.go",
            """\
            package main
            type Config struct {}
            type Service struct {}
            func (s Service) Load() {
                cfg := new(Config)
                _ = cfg
            }
        """,
        )
        assert ("Service", "Config") in _edge_pairs(r)

    def test_addr_composite_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "addr_comp.go",
            """\
            package main
            type Logger struct {}
            type App struct {}
            func (a App) Init() {
                log := &Logger{}
                _ = log
            }
        """,
        )
        assert ("App", "Logger") in _edge_pairs(r)

    def test_new_pointer_type_usage(self, tmp_path):
        r = _write(
            tmp_path,
            "new_ptr.go",
            """\
            package main
            type Target struct {}
            type Holder struct {}
            func (h Holder) Create() {
                x := new(*Target)
                _ = x
            }
        """,
        )
        assert ("Holder", "Target") in _edge_pairs(r)

    def test_new_no_args_no_crash(self, tmp_path):
        r = _write(
            tmp_path,
            "new_noargs.go",
            """\
            package main
            type S struct {}
            func (s S) Method() {
                _ = new()
            }
        """,
        )
        assert "S" in _node_names(r)
        assert len(r["edges"]) == 0

    def test_addr_composite_with_fields(self, tmp_path):
        r = _write(
            tmp_path,
            "addr_fields.go",
            """\
            package main
            type Config struct { Name string }
            type App struct {}
            func (a App) Init() {
                cfg := &Config{Name: "test"}
                _ = cfg
            }
        """,
        )
        assert ("App", "Config") in _edge_pairs(r)

    def test_all_construction_patterns_single_edge(self, tmp_path):
        r = _write(
            tmp_path,
            "all_patterns.go",
            """\
            package main
            type Repo struct {}
            type Service struct {}
            func (s Service) Run() {
                a := new(Repo)
                b := &Repo{}
                c := Repo{}
                _, _, _ = a, b, c
            }
        """,
        )
        pairs = _edge_pairs(r)
        assert ("Service", "Repo") in pairs
        assert len(r["edges"]) == 1
