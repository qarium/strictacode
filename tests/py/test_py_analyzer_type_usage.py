import textwrap

from strictacode.py.analyzer import Analyzer


def _write_py(tmp_path, filename, source):
    p = tmp_path / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(source))
    return str(p)


class TestConstructorUsage:
    def test_constructor_call(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", """\
            class Service:
                def create(self):
                    token = Token()
        """)
        a = Analyzer.file(fp)
        key = f"{fp}:Service"
        assert "Token" in a.type_usage.get(key, set())

    def test_constructor_in_init(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", """\
            class Service:
                def __init__(self):
                    self.engine = Engine()
        """)
        a = Analyzer.file(fp)
        key = f"{fp}:Service"
        assert "Engine" in a.type_usage.get(key, set())

    def test_no_class_no_usage(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", """\
            def helper():
                token = Token()
        """)
        a = Analyzer.file(fp)
        assert a.type_usage == {}

    def test_lowercase_call_not_captured(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", """\
            class Service:
                def run(self):
                    result = helper()
        """)
        a = Analyzer.file(fp)
        key = f"{fp}:Service"
        assert "helper" not in a.type_usage.get(key, set())

    def test_base_type_constructor_not_captured(self, tmp_path):
        fp = _write_py(tmp_path, "svc.py", """\
            class Service:
                def build(self):
                    items = list()
                    data = dict()
        """)
        a = Analyzer.file(fp)
        key = f"{fp}:Service"
        assert "list" not in a.type_usage.get(key, set())
        assert "dict" not in a.type_usage.get(key, set())
