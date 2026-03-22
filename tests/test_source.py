import pytest
from strictacode.source import (
    ClassSource,
    FunctionSource,
    MethodSource,
    ModuleSource,
    PackageSource,
    Sources,
    Status,
)

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_default_score(self):
        from strictacode.calc import score as score_mod
        s = Status()
        assert s.score == score_mod.Metric(value=0)

    def test_name_returns_score_status(self):
        from strictacode.calc import score as score_mod
        s = Status(score=score_mod.Metric(value=50))
        assert s.name == score_mod.Status.WARNING


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


class TestSources:
    def test_properties(self):
        src = Sources("/tmp", "python")
        assert src.path == "/tmp"
        assert src.lang == "python"
        assert src.status.reasons == []
        assert src.packages == []
        assert src.modules == []
        assert src.classes == []
        assert src.methods == []
        assert src.functions == []

    def test_loc_empty(self):
        src = Sources("/tmp", "python")
        assert src.loc == 0

    def test_repr(self):
        src = Sources("/tmp/project", "python")
        r = repr(src)
        assert "Sources" in r
        assert "/tmp/project" in r
        assert "loc=0" in r

    def test_overengineering_pressure_not_set_raises(self):
        src = Sources("/tmp", "python")
        with pytest.raises(ValueError, match="not set"):
            _ = src.overengineering_pressure


# ---------------------------------------------------------------------------
# PackageSource
# ---------------------------------------------------------------------------


class TestPackageSource:
    def test_properties(self):
        pkg = PackageSource("/tmp/pkg")
        assert pkg.path == "/tmp/pkg"
        assert pkg.name == "pkg"
        assert pkg.modules == []
        assert pkg.status.reasons == []

    def test_name_root_path(self):
        pkg = PackageSource("/")
        assert pkg.name == "<root>"

    def test_loc_empty(self):
        pkg = PackageSource("/tmp")
        assert pkg.loc == 0

    def test_repr(self):
        pkg = PackageSource("/tmp/pkg")
        r = repr(pkg)
        assert "PackageSource" in r
        assert "pkg" in r
        assert "loc=0" in r


# ---------------------------------------------------------------------------
# ModuleSource
# ---------------------------------------------------------------------------


class TestModuleSource:
    def test_properties(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        assert mod.path == tmp_py_file
        assert mod.name == "sample.py"

    def test_loc(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        # sample.py: 1 comment + 8 code = 9 non-blank
        assert mod.loc == 9

    def test_loc_with_ignore_prefixes(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file, comment_line_prefixes=["#"])
        # sample.py without comments: 8 code lines
        assert mod.loc == 8

    def test_content(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        assert "def foo():" in mod.content
        assert "def bar():" in mod.content

    def test_classes_and_functions_empty(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        assert mod.classes == []
        assert mod.functions == []
        assert mod.methods == []

    def test_repr(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        r = repr(mod)
        assert "ModuleSource" in r
        assert "sample.py" in r

    def test_overengineering_pressure_default_zero(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        assert mod.overengineering_pressure.score == 0

    def test_overengineering_pressure_setter(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        from strictacode.calc.pressure import overengineering
        mod.overengineering_pressure = overengineering.Metric(42)
        assert mod.overengineering_pressure.score == 42

    def test_compile_sets_status_score(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        # Add a class so complexity > 0
        cls = ClassSource(mod, "Foo", lineno=2, endline=4, complexity=5,
                          comment_line_prefixes=["#"],
                          comment_code_blocks=[('"""', '"""')])
        mod.classes.append(cls)
        assert mod.complexity.score > 0
        assert mod.status.score.value == 0
        mod.compile()
        assert mod.status.score.value > 0


# ---------------------------------------------------------------------------
# ClassSource
# ---------------------------------------------------------------------------


class TestClassSource:
    def test_properties(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "MyClass", lineno=2, endline=5, complexity=3)
        assert cls.module is mod
        assert cls.name == "MyClass"
        assert cls.lineno == 2
        assert cls.endline == 5
        assert cls.methods == []

    def test_loc(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo", lineno=2, endline=10)
        # Lines 2-10: def foo(), x=1, return x, blank, def bar(), y=2, if y>0:, return y, return 0
        # = 8 non-blank
        assert cls.loc == 8

    def test_loc_from_methods(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo", lineno=2, endline=10, loc_from_methods=True)
        assert cls.loc == 0  # no methods added

    def test_loc_from_methods_with_methods(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo", lineno=2, endline=10, loc_from_methods=True)
        method = MethodSource(mod, cls, "bar", lineno=6, endline=10,
                              comment_line_prefixes=["#"],
                              comment_code_blocks=[('"""', '"""')])
        cls.methods.append(method)
        # bar spans lines 6-10: 5 non-blank
        assert cls.loc == 5

    def test_content(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo", lineno=2, endline=4)
        content = cls.content
        assert "def foo():" in content

    def test_repr(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo")
        assert "Foo" in repr(cls)

    def test_overengineering_pressure_default_zero(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo")
        assert cls.overengineering_pressure.score == 0

    def test_overengineering_pressure_setter(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        from strictacode.calc.pressure import overengineering
        cls = ClassSource(mod, "Foo")
        cls.overengineering_pressure = overengineering.Metric(55)
        assert cls.overengineering_pressure.score == 55


# ---------------------------------------------------------------------------
# MethodSource
# ---------------------------------------------------------------------------


class TestMethodSource:
    def test_properties(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo")
        method = MethodSource(mod, cls, "my_method", lineno=3, endline=5, complexity=2)
        assert method.module is mod
        assert method.cls is cls
        assert method.name == "my_method"
        assert method.lineno == 3
        assert method.endline == 5
        assert method.closures == []

    def test_loc(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo")
        method = MethodSource(mod, cls, "bar", lineno=6, endline=10)
        # lines 6-10 in sample.py:
        # 6: def bar():    7: y = 2   8: if y > 0:  9: return y  10: return 0
        # = 5 non-blank
        assert method.loc == 5

    def test_content(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo")
        method = MethodSource(mod, cls, "foo", lineno=2, endline=4)
        assert "def foo():" in method.content

    def test_repr(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo")
        method = MethodSource(mod, cls, "bar")
        assert "bar" in repr(method)
        assert "Foo" in repr(method)


# ---------------------------------------------------------------------------
# FunctionSource
# ---------------------------------------------------------------------------


class TestFunctionSource:
    def test_properties(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        func = FunctionSource(mod, "my_func", lineno=2, endline=5, complexity=1)
        assert func.module is mod
        assert func.name == "my_func"
        assert func.lineno == 2
        assert func.endline == 5
        assert func.closures == []

    def test_loc(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        func = FunctionSource(mod, "foo", lineno=2, endline=4)
        # lines 2,3,4: def foo():, x = 1, return x = 3 non-blank
        assert func.loc == 3

    def test_content(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        func = FunctionSource(mod, "foo", lineno=2, endline=4)
        assert "def foo():" in func.content

    def test_repr(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        func = FunctionSource(mod, "hello")
        assert "hello" in repr(func)


# ---------------------------------------------------------------------------
# Closures
# ---------------------------------------------------------------------------


class TestClosures:
    def test_method_closures(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        cls = ClassSource(mod, "Foo")
        method = MethodSource(mod, cls, "outer", lineno=2, endline=10)
        inner = FunctionSource(mod, "inner", lineno=3, endline=5, complexity=1)
        method.closures.append(inner)
        assert len(method.closures) == 1
        assert method.closures[0].name == "inner"

    def test_function_closures(self, tmp_py_file):
        mod = ModuleSource(tmp_py_file)
        outer = FunctionSource(mod, "outer", lineno=2, endline=10)
        inner = FunctionSource(mod, "inner", lineno=3, endline=5, complexity=1)
        outer.closures.append(inner)
        assert len(outer.closures) == 1
