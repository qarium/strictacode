from unittest.mock import patch

import pytest
from strictacode.js.loader import JSLoder

# ---------------------------------------------------------------------------
# JSLoder class attributes
# ---------------------------------------------------------------------------


class TestJSLoderAttributes:
    def test_lang(self):
        assert JSLoder.__lang__ == "javascript"

    def test_comment_line_prefixes(self):
        assert "//" in JSLoder.__comment_line_prefixes__

    def test_comment_code_blocks(self):
        assert ("/*", "*/") in JSLoder.__comment_code_blocks__


# ---------------------------------------------------------------------------
# _create_item
# ---------------------------------------------------------------------------


class TestCreateItem:
    def test_creates_class_item(self):
        from strictacode.js.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(type="class", name="UserService", lineno=1, endline=30,
                            complexity=8, classname=None, methods=[], closures=[])
        assert item.type == FileItemTypes.CLASS
        assert item.name == "UserService"

    def test_creates_function_item(self):
        from strictacode.js.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(type="function", name="init", lineno=5, endline=10,
                            complexity=2, methods=[], closures=[])
        assert item.type == FileItemTypes.FUNCTION

    def test_creates_method_item(self):
        from strictacode.js.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(type="method", name="getUser", lineno=10, endline=20,
                            complexity=3, classname="UserService",
                            methods=[], closures=[])
        assert item.type == FileItemTypes.METHOD
        assert item.class_name == "UserService"


# ---------------------------------------------------------------------------
# collector.collect — mock subprocess
# ---------------------------------------------------------------------------


def _make_js_collector_json(root):
    """Build JS-collector-like JSON with a real file path under root."""
    src_dir = root / "src"
    src_dir.mkdir()
    filepath = src_dir / "index.js"
    filepath.write_text("class Router {}\n")

    return {
        str(filepath): [
            {
                "type": "class",
                "name": "Router",
                "lineno": 5,
                "endline": 40,
                "complexity": 6,
                "methods": [
                    {
                        "type": "method",
                        "name": "handle",
                        "lineno": 10,
                        "endline": 30,
                        "complexity": 4,
                        "classname": "Router",
                        "closures": [],
                    },
                ],
                "closures": [],
            },
            {
                "type": "function",
                "name": "bootstrap",
                "lineno": 45,
                "endline": 50,
                "complexity": 1,
                "closures": [],
            },
        ],
    }


class TestJSLoderCollect:
    @patch("strictacode.js.collector.collect")
    def test_collect_returns_file_items(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_js_collector_json(tmp_path)
        loader = JSLoder(str(tmp_path))

        result = loader.collect()

        filepath = str(tmp_path / "src" / "index.js")
        assert filepath in result
        assert len(result[filepath]) == 2

        from strictacode.loader import FileItemTypes
        assert result[filepath][0].type == FileItemTypes.CLASS
        assert result[filepath][0].name == "Router"
        assert result[filepath][1].type == FileItemTypes.FUNCTION
        assert result[filepath][1].name == "bootstrap"

    @patch("strictacode.js.collector.collect")
    def test_collect_with_method(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_js_collector_json(tmp_path)
        loader = JSLoder(str(tmp_path))
        result = loader.collect()

        filepath = str(tmp_path / "src" / "index.js")
        cls_item = result[filepath][0]
        assert len(cls_item.methods) == 1
        assert cls_item.methods[0].name == "handle"
        assert cls_item.methods[0].class_name == "Router"

    @patch("strictacode.js.collector.collect")
    def test_collect_node_error_raises(self, mock_collect, tmp_path):
        mock_collect.side_effect = RuntimeError("Cannot find module @babel/parser")
        loader = JSLoder(str(tmp_path))

        with pytest.raises(RuntimeError, match="@babel/parser"):
            loader.collect()


# ---------------------------------------------------------------------------
# analyzer.analyze — mock subprocess
# ---------------------------------------------------------------------------


class TestJSLoderBuild:
    @patch("strictacode.js.analyzer.analyze")
    @patch("strictacode.js.collector.collect")
    def test_build_adds_graph_nodes(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_js_collector_json(tmp_path)

        src_dir = tmp_path / "src"
        analyzer_data = {
            "nodes": [f"{src_dir}/index.js:Router", f"{src_dir}/index.js:Middleware"],
            "edges": [
                {"source": f"{src_dir}/index.js:Router", "target": f"{src_dir}/index.js:Middleware"},
            ],
        }
        mock_analyze.return_value = analyzer_data
        loader = JSLoder(str(tmp_path))
        loader.load()

        nodes = loader.sources.graph.nodes
        assert f"{src_dir}/index.js:Router" in nodes

    @patch("strictacode.js.analyzer.analyze")
    @patch("strictacode.js.collector.collect")
    def test_build_adds_graph_edges(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_js_collector_json(tmp_path)

        src_dir = tmp_path / "src"
        analyzer_data = {
            "nodes": [f"{src_dir}/index.js:Router", f"{src_dir}/index.js:Middleware"],
            "edges": [
                {"source": f"{src_dir}/index.js:Router", "target": f"{src_dir}/index.js:Middleware"},
            ],
        }
        mock_analyze.return_value = analyzer_data
        loader = JSLoder(str(tmp_path))
        loader.load()

        edges = loader.sources.graph.edges
        assert len(edges) == 1
        assert f"{src_dir}/index.js:Router" in edges
        assert f"{src_dir}/index.js:Middleware" in edges[f"{src_dir}/index.js:Router"]

    @patch("strictacode.js.analyzer.analyze")
    @patch("strictacode.js.collector.collect")
    def test_build_empty_analyzer(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_js_collector_json(tmp_path)
        mock_analyze.return_value = {"nodes": [], "edges": []}
        loader = JSLoder(str(tmp_path))
        loader.load()

        assert len(loader.sources.graph.nodes) == 0

    @patch("strictacode.js.analyzer.analyze")
    @patch("strictacode.js.collector.collect")
    def test_build_filters_uncollected_nodes(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_js_collector_json(tmp_path)

        src_dir = tmp_path / "src"
        analyzer_data = {
            "nodes": [f"{src_dir}/index.js:Router", "other.js:SomeClass"],
            "edges": [
                {"source": f"{src_dir}/index.js:Router", "target": "other.js:SomeClass"},
            ],
        }
        mock_analyze.return_value = analyzer_data
        loader = JSLoder(str(tmp_path))
        loader.load()

        nodes = loader.sources.graph.nodes
        assert f"{src_dir}/index.js:Router" in nodes
        assert "other.js:SomeClass" not in nodes
