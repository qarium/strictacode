import textwrap

import pytest

from strictacode.loader import (
    Loader,
    FileItem,
    FileItemTypes,
    _load_closures,
)


# ---------------------------------------------------------------------------
# FileItem
# ---------------------------------------------------------------------------


class TestFileItem:
    def test_defaults(self):
        item = FileItem(type=FileItemTypes.CLASS, name="Foo")
        assert item.type == FileItemTypes.CLASS
        assert item.name == "Foo"
        assert item.lineno == 0
        assert item.endline == 0
        assert item.complexity == 0
        assert item.class_name is None
        assert item.methods == []
        assert item.closures == []

    def test_all_fields(self):
        item = FileItem(
            type=FileItemTypes.METHOD,
            name="bar",
            lineno=5,
            endline=10,
            complexity=3,
            class_name="Foo",
        )
        assert item.lineno == 5
        assert item.endline == 10
        assert item.complexity == 3
        assert item.class_name == "Foo"


# ---------------------------------------------------------------------------
# FileItemTypes
# ---------------------------------------------------------------------------


class TestFileItemTypes:
    def test_values(self):
        assert FileItemTypes.CLASS == "class"
        assert FileItemTypes.METHOD == "method"
        assert FileItemTypes.FUNCTION == "function"

    def test_is_str_enum(self):
        assert FileItemTypes.CLASS == "class"
        assert isinstance(FileItemTypes.CLASS, str)


# ---------------------------------------------------------------------------
# _load_closures
# ---------------------------------------------------------------------------


class TestLoadClosures:
    def test_loads_nested_closures(self, tmp_path):
        filepath = str(tmp_path / "mod.py")
        tmp_path.joinpath("mod.py").write_text("pass")

        from strictacode.source import ModuleSource, FunctionSource

        module = ModuleSource(filepath)
        func = FunctionSource(module, "outer", lineno=1, endline=1, complexity=2)

        closure_1 = FileItem(
            type=FileItemTypes.FUNCTION,
            name="inner1",
            lineno=1,
            endline=1,
            complexity=1,
        )
        closure_2 = FileItem(
            type=FileItemTypes.FUNCTION,
            name="inner2",
            lineno=1,
            endline=1,
            complexity=1,
            closures=[
                FileItem(
                    type=FileItemTypes.FUNCTION,
                    name="deep_inner",
                    lineno=1,
                    endline=1,
                    complexity=1,
                ),
            ],
        )

        _load_closures(module, func, [closure_1, closure_2])

        assert len(func.closures) == 2
        assert func.closures[0].name == "inner1"
        assert func.closures[1].name == "inner2"
        assert len(func.closures[1].closures) == 1
        assert func.closures[1].closures[0].name == "deep_inner"

    def test_no_closures(self, tmp_path):
        filepath = str(tmp_path / "mod.py")
        tmp_path.joinpath("mod.py").write_text("pass")

        from strictacode.source import ModuleSource, FunctionSource

        module = ModuleSource(filepath)
        func = FunctionSource(module, "simple", lineno=1, endline=1, complexity=1)

        _load_closures(module, func, [])

        assert func.closures == []


# ---------------------------------------------------------------------------
# Loader (abstract - test via concrete subclass)
# ---------------------------------------------------------------------------


class ConcreteLoader(Loader):
    __lang__ = "test"
    __comment_line_prefixes__ = ["#"]

    def collect(self):
        return {}

    def build(self):
        pass


class TestLoaderInit:
    def test_defaults(self):
        loader = ConcreteLoader("/tmp")
        assert loader.root == "/tmp"
        assert loader.sources.lang == "test"

    def test_class_loc_from_methods(self):
        loader = ConcreteLoader("/tmp", class_loc_from_methods=True)
        assert loader._class_loc_from_methods is True

    def test_exclude_patterns(self):
        loader = ConcreteLoader("/tmp", exclude_patterns=["vendor/"])
        assert loader._exclude_patterns == ["vendor/"]


class TestShouldExcludeFile:
    def test_no_patterns_includes_all(self, tmp_path):
        loader = ConcreteLoader(str(tmp_path))
        some_file = tmp_path / "some.py"
        some_file.write_text("pass")
        assert loader._should_exclude_file(str(some_file)) is False

    def test_excluded_by_exclude_pattern(self, tmp_path):
        vendor_dir = tmp_path / "vendor"
        vendor_dir.mkdir()
        vendor_file = vendor_dir / "lib.go"
        vendor_file.write_text("pass")

        loader = ConcreteLoader(str(tmp_path), exclude_patterns=[str(vendor_dir)])
        assert loader._should_exclude_file(str(vendor_file)) is True

    def test_included_by_include_pattern(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        src_file = src_dir / "main.py"
        src_file.write_text("pass")
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        other_file = other_dir / "util.py"
        other_file.write_text("pass")

        loader = ConcreteLoader(str(tmp_path), include_patterns=[str(src_dir)])
        assert loader._should_exclude_file(str(src_file)) is False
        assert loader._should_exclude_file(str(other_file)) is True

    def test_child_of_excluded_dir(self, tmp_path):
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        child = build_dir / "lib" / "app.go"
        child.parent.mkdir(parents=True)
        child.write_text("pass")

        loader = ConcreteLoader(str(tmp_path), exclude_patterns=[str(build_dir)])
        assert loader._should_exclude_file(str(child)) is True

    def test_ignores_includes_exclude_patterns(self, tmp_path):
        loader = ConcreteLoader(str(tmp_path), exclude_patterns=["vendor/", "build/"])
        assert "vendor/" in loader.ignores
        assert "build/" in loader.ignores

    def test_include_and_exclude_exclude_wins(self, tmp_path):
        """File in both include and exclude dirs should be excluded."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        src_file = src_dir / "main.py"
        src_file.write_text("pass")

        loader = ConcreteLoader(
            str(tmp_path),
            include_patterns=[str(src_dir)],
            exclude_patterns=[str(src_dir)],
        )
        # File is included by include_patterns but excluded by exclude_patterns
        assert loader._should_exclude_file(str(src_file)) is True


class TestLoaderLoad:
    def _make_stub_loader(self, root, collect_data=None, **kwargs):
        """Create a Loader subclass that returns the given collect data."""
        _collect_data = collect_data or {}

        class StubLoader(Loader):
            __lang__ = "test"
            __comment_line_prefixes__ = ["#"]

            def __init__(self, root, **kw):
                super().__init__(root, **kw)

            def collect(self):
                return _collect_data

            def build(self):
                pass

        return StubLoader(root, **kwargs)

    def test_load_returns_sources(self, tmp_path):
        loader = ConcreteLoader(str(tmp_path))
        sources = loader.load()
        assert sources.lang == "test"

    def test_load_empty_project(self, tmp_path):
        loader = ConcreteLoader(str(tmp_path))
        sources = loader.load()
        assert sources.loc == 0
        assert sources.packages == []
        assert sources.modules == []

    def test_load_with_class_and_method(self, tmp_path):
        mod_file = tmp_path / "test.py"
        mod_file.write_text(textwrap.dedent("""\
            class Foo:
                def bar(self):
                    pass
        """))
        collect_data = {
            str(mod_file): [
                FileItem(
                    type=FileItemTypes.CLASS,
                    name="Foo",
                    lineno=1,
                    endline=4,
                    complexity=1,
                    methods=[
                        FileItem(
                            type=FileItemTypes.METHOD,
                            name="bar",
                            lineno=2,
                            endline=3,
                            complexity=0,
                            class_name="Foo",
                        ),
                    ],
                ),
            ],
        }
        loader = self._make_stub_loader(str(tmp_path), collect_data)
        sources = loader.load()

        assert len(sources.classes) == 1
        assert sources.classes[0].name == "Foo"
        assert len(sources.methods) == 1
        assert sources.methods[0].name == "bar"
        assert sources.methods[0].cls is sources.classes[0]
        assert sources.classes[0].module is sources.modules[0]

    def test_load_with_functions(self, tmp_path):
        mod_file = tmp_path / "util.py"
        mod_file.write_text("def helper(): pass\n")
        collect_data = {
            str(mod_file): [
                FileItem(
                    type=FileItemTypes.FUNCTION,
                    name="helper",
                    lineno=1,
                    endline=1,
                    complexity=0,
                ),
            ],
        }
        loader = self._make_stub_loader(str(tmp_path), collect_data)
        sources = loader.load()
        assert len(sources.functions) == 1
        assert sources.functions[0].name == "helper"

    def test_load_with_closures(self, tmp_path):
        mod_file = tmp_path / "mod.py"
        mod_file.write_text("def outer(): pass\n")
        collect_data = {
            str(mod_file): [
                FileItem(
                    type=FileItemTypes.FUNCTION,
                    name="outer",
                    lineno=1,
                    endline=1,
                    complexity=1,
                    closures=[
                        FileItem(
                            type=FileItemTypes.FUNCTION,
                            name="inner",
                            lineno=1,
                            endline=1,
                            complexity=1,
                        ),
                    ],
                ),
            ],
        }
        loader = self._make_stub_loader(str(tmp_path), collect_data)
        sources = loader.load()
        assert len(sources.functions) == 1
        assert len(sources.functions[0].closures) == 1
        assert sources.functions[0].closures[0].name == "inner"

    def test_load_excludes_files_by_pattern(self, tmp_path):
        mod_file = tmp_path / "test.py"
        mod_file.write_text("pass")
        excluded_dir = tmp_path / "excluded"
        excluded_dir.mkdir()
        excluded_file = excluded_dir / "skip.py"
        excluded_file.write_text("pass")

        collect_data = {
            str(mod_file): [
                FileItem(type=FileItemTypes.FUNCTION, name="f1", lineno=1, endline=1),
            ],
            str(excluded_file): [
                FileItem(type=FileItemTypes.FUNCTION, name="f2", lineno=1, endline=1),
            ],
        }
        loader = self._make_stub_loader(str(tmp_path), collect_data,
                                          exclude_patterns=[str(excluded_dir)])
        sources = loader.load()
        assert len(sources.functions) == 1
        assert sources.functions[0].name == "f1"

    def test_unknown_item_type_raises(self, tmp_path):
        mod_file = tmp_path / "test.py"
        mod_file.write_text("pass")
        collect_data = {
            str(mod_file): [
                FileItem(type="unknown_type", name="x"),
            ],
        }
        loader = self._make_stub_loader(str(tmp_path), collect_data)
        with pytest.raises(ValueError, match="Unknown metric type"):
            loader.load()
