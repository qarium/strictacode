import textwrap

from strictacode.py.loader import PyLoder


def _write(tmp_path, filename, source):
    p = tmp_path / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(source))
    return str(p)


def _file_item(name, lineno=1, endline=1, complexity=1):
    return type("F", (), {
        "type": "class", "name": name, "lineno": lineno,
        "endline": endline, "complexity": complexity,
        "classname": None, "methods": [], "closures": [],
    })()


class TestIntegration:
    def test_inheritance_only(self, tmp_path):
        _write(tmp_path, "base.py", "class Base: pass\n")
        _write(tmp_path, "child.py", "class Child(Base): pass\n")

        loader = PyLoder(str(tmp_path))
        loader.collect = lambda: {
            str(tmp_path / "base.py"): [_file_item("Base")],
            str(tmp_path / "child.py"): [_file_item("Child")],
        }
        loader.load()

        graph = loader.sources.graph
        assert f"{tmp_path / 'child.py'}:Child" in graph.nodes
        assert f"{tmp_path / 'base.py'}:Base" in graph.nodes

    def test_constructor_call_creates_edge(self, tmp_path):
        _write(tmp_path, "models.py", "class Token: pass\n")
        svc = _write(tmp_path, "svc.py", """\
            from models import Token
            class Service:
                def create(self):
                    token = Token()
        """)

        loader = PyLoder(str(tmp_path))
        loader.collect = lambda: {
            str(tmp_path / "models.py"): [_file_item("Token")],
            str(tmp_path / "svc.py"): [_file_item("Service", lineno=2, endline=5)],
        }
        loader.load()

        graph = loader.sources.graph
        svc_edges = graph.edges.get(f"{svc}:Service", set())
        token_targets = [t for t in svc_edges if "Token" in t]
        assert len(token_targets) >= 1

    def test_no_constructor_no_extra_edges(self, tmp_path):
        _write(tmp_path, "base.py", "class Base: pass\n")
        child = _write(tmp_path, "child.py", "class Child(Base): pass\n")

        loader = PyLoder(str(tmp_path))
        loader.collect = lambda: {
            str(tmp_path / "base.py"): [_file_item("Base")],
            str(tmp_path / "child.py"): [_file_item("Child")],
        }
        loader.load()

        graph = loader.sources.graph
        child_edges = graph.edges.get(f"{child}:Child", set())
        assert len(child_edges) == 1  # Only the inheritance edge to Base

    def test_metaclass_creates_edge(self, tmp_path):
        _write(tmp_path, "meta.py", "class SingletonMeta: pass\n")
        svc = _write(tmp_path, "svc.py", """\
            from meta import SingletonMeta
            class Service(metaclass=SingletonMeta):
                pass
        """)

        loader = PyLoder(str(tmp_path))
        loader.collect = lambda: {
            str(tmp_path / "meta.py"): [_file_item("SingletonMeta")],
            str(tmp_path / "svc.py"): [_file_item("Service", lineno=2, endline=4)],
        }
        loader.load()

        graph = loader.sources.graph
        svc_edges = graph.edges.get(f"{svc}:Service", set())
        meta_targets = [t for t in svc_edges if "SingletonMeta" in t]
        assert len(meta_targets) >= 1
