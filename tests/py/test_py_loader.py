from unittest.mock import MagicMock, patch

import pytest
from strictacode.py.loader import PyLoder

# ---------------------------------------------------------------------------
# PyLoder class attributes
# ---------------------------------------------------------------------------


class TestPyLoaderAttributes:
    def test_lang(self):
        assert PyLoder.__lang__ == "python"

    def test_comment_line_prefixes(self):
        assert "#" in PyLoder.__comment_line_prefixes__

    def test_comment_code_blocks(self):
        assert ('"""', '"""') in PyLoder.__comment_code_blocks__
        assert ("'''", "'''") in PyLoder.__comment_code_blocks__

    def test_ignore_dirs(self):
        assert ".venv" in PyLoder.__ignore_dirs__
        assert "venv" in PyLoder.__ignore_dirs__


# ---------------------------------------------------------------------------
# _create_item
# ---------------------------------------------------------------------------


class TestCreateItem:
    def test_creates_class_item(self):
        from strictacode.loader import FileItemTypes
        from strictacode.py.loader import _create_item

        item = _create_item(
            type="class", name="Foo", lineno=1, endline=10, complexity=3, classname=None, methods=[], closures=[]
        )
        assert item.type == FileItemTypes.CLASS
        assert item.name == "Foo"
        assert item.lineno == 1
        assert item.endline == 10
        assert item.complexity == 3
        assert item.class_name is None

    def test_creates_method_item(self):
        from strictacode.loader import FileItemTypes
        from strictacode.py.loader import _create_item

        item = _create_item(
            type="method", name="bar", lineno=5, endline=15, complexity=2, classname="Foo", methods=[], closures=[]
        )
        assert item.type == FileItemTypes.METHOD
        assert item.name == "bar"
        assert item.lineno == 5
        assert item.endline == 15
        assert item.complexity == 2
        assert item.class_name == "Foo"

    def test_creates_function_item(self):
        from strictacode.loader import FileItemTypes
        from strictacode.py.loader import _create_item

        item = _create_item(type="function", name="baz", lineno=20, endline=25, complexity=1, methods=[], closures=[])
        assert item.type == FileItemTypes.FUNCTION
        assert item.lineno == 20
        assert item.endline == 25
        assert item.complexity == 1

    def test_creates_nested_closures(self):
        from strictacode.py.loader import _create_item

        item = _create_item(
            type="function",
            name="outer",
            lineno=1,
            endline=10,
            complexity=2,
            closures=[
                {
                    "type": "function",
                    "name": "inner",
                    "lineno": 3,
                    "endline": 8,
                    "complexity": 1,
                    "methods": [],
                    "closures": [],
                },
            ],
        )
        assert len(item.closures) == 1
        assert item.closures[0].name == "inner"


# ---------------------------------------------------------------------------
# collect() — mock subprocess
# ---------------------------------------------------------------------------


def _make_radon_json(root, filename="main.py"):
    """Build radon-like JSON with a real file path under root."""
    filepath = str(root / filename)
    return {
        filepath: [
            {
                "type": "class",
                "name": "MyClass",
                "lineno": 1,
                "endline": 20,
                "complexity": 5,
                "classname": None,
                "methods": [
                    {
                        "type": "method",
                        "name": "do_stuff",
                        "lineno": 5,
                        "endline": 15,
                        "complexity": 3,
                        "classname": "MyClass",
                        "closures": [],
                    },
                ],
                "closures": [],
            },
            {
                "type": "function",
                "name": "helper",
                "lineno": 22,
                "endline": 30,
                "complexity": 2,
                "methods": [],
                "closures": [],
            },
        ],
    }


class TestPyLoaderCollect:
    @patch("strictacode.py.collector.collect")
    def test_collect_returns_file_items(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_radon_json(tmp_path)
        loader = PyLoder(str(tmp_path))

        result = loader.collect()

        filepath = str(tmp_path / "main.py")
        assert filepath in result
        assert len(result[filepath]) == 2

        from strictacode.loader import FileItemTypes

        assert result[filepath][0].type == FileItemTypes.CLASS
        assert result[filepath][0].name == "MyClass"
        assert result[filepath][1].type == FileItemTypes.FUNCTION
        assert result[filepath][1].name == "helper"

    @patch("strictacode.py.collector.collect")
    def test_collect_with_method(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_radon_json(tmp_path)
        loader = PyLoder(str(tmp_path))
        result = loader.collect()

        filepath = str(tmp_path / "main.py")
        cls_item = result[filepath][0]
        assert len(cls_item.methods) == 1
        assert cls_item.methods[0].name == "do_stuff"

    @patch("strictacode.py.collector.collect")
    def test_collect_radon_error_raises(self, mock_collect, tmp_path):
        mock_collect.side_effect = RuntimeError("radon failed")
        loader = PyLoder(str(tmp_path))

        with pytest.raises(RuntimeError, match="radon failed"):
            loader.collect()


# ---------------------------------------------------------------------------
# build() — mock Analyzer.file
# ---------------------------------------------------------------------------


class TestPyLoaderBuild:
    @patch("strictacode.py.analyzer.Analyzer.file")
    @patch("strictacode.py.collector.collect")
    def test_build_adds_graph_nodes(self, mock_collect, mock_analyzer_file, tmp_path):
        py_file = tmp_path / "main.py"
        py_file.write_text("class MyClass: pass\n")

        mock_collect.return_value = _make_radon_json(tmp_path)

        mock_analyzer = MagicMock()
        mock_analyzer.classes = {
            str(py_file) + ":MyClass": {"methods": 2},
        }
        mock_analyzer.class_bases = {
            str(py_file) + ":MyClass": ["BaseClass"],
        }
        mock_analyzer_file.return_value = mock_analyzer

        loader = PyLoder(str(tmp_path))
        loader.load()

        nodes = loader.sources.graph.nodes
        assert f"{py_file}:MyClass" in nodes

    @patch("strictacode.py.analyzer.Analyzer.file")
    @patch("strictacode.py.collector.collect")
    def test_build_adds_graph_edges(self, mock_collect, mock_analyzer_file, tmp_path):
        py_file = tmp_path / "main.py"
        py_file.write_text("class MyClass: pass\n")

        mock_collect.return_value = _make_radon_json(tmp_path)

        mock_analyzer = MagicMock()
        mock_analyzer.classes = {
            str(py_file) + ":MyClass": {"methods": 2},
        }
        mock_analyzer.class_bases = {
            str(py_file) + ":MyClass": ["BaseClass"],
        }
        mock_analyzer_file.return_value = mock_analyzer

        loader = PyLoder(str(tmp_path))
        loader.load()

        edges = loader.sources.graph.edges
        assert f"{py_file}:MyClass" in edges
        assert "BaseClass" in edges[f"{py_file}:MyClass"]

    @patch("strictacode.py.analyzer.Analyzer.file")
    @patch("strictacode.py.collector.collect")
    def test_build_skips_none_analyzer(self, mock_collect, mock_analyzer_file, tmp_path):
        py_file = tmp_path / "main.py"
        py_file.write_text("pass\n")

        mock_collect.return_value = _make_radon_json(tmp_path)
        mock_analyzer_file.return_value = None

        loader = PyLoder(str(tmp_path))
        loader.load()

        assert len(loader.sources.graph.nodes) == 0


# ---------------------------------------------------------------------------
# build() — usage edges
# ---------------------------------------------------------------------------


class TestPyLoaderBuildUsageEdges:
    @patch("strictacode.py.analyzer.Analyzer.file")
    @patch("strictacode.py.collector.collect")
    def test_build_resolves_type_usage_edges(self, mock_collect, mock_analyzer_file, tmp_path):
        models_file = tmp_path / "models.py"
        svc_file = tmp_path / "svc.py"
        models_file.write_text("class User: pass\nclass Token: pass\n")
        svc_file.write_text("from models import User, Token\nclass Service: pass\n")

        mock_collect.return_value = {
            str(models_file): [
                {
                    "type": "class",
                    "name": "User",
                    "lineno": 1,
                    "endline": 1,
                    "complexity": 1,
                    "classname": None,
                    "methods": [],
                    "closures": [],
                }
            ],
            str(svc_file): [
                {
                    "type": "class",
                    "name": "Service",
                    "lineno": 2,
                    "endline": 2,
                    "complexity": 1,
                    "classname": None,
                    "methods": [],
                    "closures": [],
                }
            ],
        }

        mock_models = MagicMock()
        mock_models.classes = {f"{models_file}:User": {"methods": 0}, f"{models_file}:Token": {"methods": 0}}
        mock_models.class_bases = {}
        mock_models.import_map = {}
        mock_models.type_usage = {}

        mock_svc = MagicMock()
        mock_svc.classes = {f"{svc_file}:Service": {"methods": 1}}
        mock_svc.class_bases = {}
        mock_svc.import_map = {"User": "User", "Token": "Token"}
        mock_svc.type_usage = {f"{svc_file}:Service": {"User", "Token"}}

        def _file_side_effect(filepath):
            if filepath == str(models_file):
                return mock_models
            if filepath == str(svc_file):
                return mock_svc
            return None

        mock_analyzer_file.side_effect = _file_side_effect

        loader = PyLoder(str(tmp_path))
        loader.load()

        edges = loader.sources.graph.edges
        assert f"{svc_file}:Service" in edges
        assert f"{models_file}:User" in edges[f"{svc_file}:Service"]
        assert f"{models_file}:Token" in edges[f"{svc_file}:Service"]

    @patch("strictacode.py.analyzer.Analyzer.file")
    @patch("strictacode.py.collector.collect")
    def test_build_no_duplicate_edges(self, mock_collect, mock_analyzer_file, tmp_path):
        models_file = tmp_path / "models.py"
        svc_file = tmp_path / "svc.py"
        models_file.write_text("class Base: pass\n")
        svc_file.write_text("from models import Base\nclass Service(Base): pass\n")

        mock_collect.return_value = {
            str(models_file): [
                {
                    "type": "class",
                    "name": "Base",
                    "lineno": 1,
                    "endline": 1,
                    "complexity": 1,
                    "classname": None,
                    "methods": [],
                    "closures": [],
                }
            ],
            str(svc_file): [
                {
                    "type": "class",
                    "name": "Service",
                    "lineno": 2,
                    "endline": 2,
                    "complexity": 1,
                    "classname": None,
                    "methods": [],
                    "closures": [],
                }
            ],
        }

        mock_models = MagicMock()
        mock_models.classes = {f"{models_file}:Base": {"methods": 0}}
        mock_models.class_bases = {}
        mock_models.import_map = {}
        mock_models.type_usage = {}

        mock_svc = MagicMock()
        mock_svc.classes = {f"{svc_file}:Service": {"methods": 0}}
        mock_svc.class_bases = {f"{svc_file}:Service": ["Base"]}
        mock_svc.import_map = {"Base": "Base"}
        mock_svc.type_usage = {f"{svc_file}:Service": {"Base"}}

        def _file_side_effect(filepath):
            if filepath == str(models_file):
                return mock_models
            if filepath == str(svc_file):
                return mock_svc
            return None

        mock_analyzer_file.side_effect = _file_side_effect

        loader = PyLoder(str(tmp_path))
        loader.load()

        svc_edges = loader.sources.graph.edges.get(f"{svc_file}:Service", set())
        # Should have exactly one edge to Base (not duplicated)
        base_targets = [t for t in svc_edges if "Base" in t]
        assert len(base_targets) == 1
