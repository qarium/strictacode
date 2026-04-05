import textwrap

from strictacode.py.analyzer import Analyzer


def _write_py(tmp_path, filename, source):
    p = tmp_path / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(source))
    return str(p)


class TestExtractImports:
    def test_from_import(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", "from models import User")
        a = Analyzer.file(fp)
        assert a.import_map.get("User") is not None

    def test_import_module(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", "import os")
        a = Analyzer.file(fp)
        assert "os" in a.import_map

    def test_from_import_as(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", "from models import User as U")
        a = Analyzer.file(fp)
        assert "U" in a.import_map

    def test_no_imports(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", "x = 1\n")
        a = Analyzer.file(fp)
        assert a.import_map == {}

    def test_relative_import(self, tmp_path):
        fp = _write_py(tmp_path, "pkg/svc.py", "from .models import User")
        a = Analyzer.file(fp)
        assert "User" in a.import_map

    def test_multiple_names_in_from(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", "from models import User, Token")
        a = Analyzer.file(fp)
        assert "User" in a.import_map
        assert "Token" in a.import_map


class TestMetaclass:
    def test_metaclass_in_class_bases(self, tmp_path):
        fp = _write_py(
            tmp_path,
            "svc.py",
            """\
            class Singleton(type):
                pass
            class Service(metaclass=Singleton):
                pass
        """,
        )
        a = Analyzer.file(fp)
        key = f"{fp}:Service"
        assert "Singleton" in a.class_bases.get(key, [])

    def test_metaclass_with_base_class(self, tmp_path):
        fp = _write_py(
            tmp_path,
            "svc.py",
            """\
            class Base:
                pass
            class Service(Base, metaclass=Singleton):
                pass
        """,
        )
        a = Analyzer.file(fp)
        key = f"{fp}:Service"
        assert "Base" in a.class_bases.get(key, [])
        assert "Singleton" in a.class_bases.get(key, [])

    def test_no_metaclass(self, tmp_path):
        fp = _write_py(
            tmp_path,
            "svc.py",
            """\
            class Service:
                pass
        """,
        )
        a = Analyzer.file(fp)
        key = f"{fp}:Service"
        assert a.class_bases.get(key, []) == []
