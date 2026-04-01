from unittest.mock import patch

import pytest
from strictacode.kotlin.loader import KotlinLoder


class TestKotlinLoderAttributes:
    def test_lang(self):
        assert KotlinLoder.__lang__ == "kotlin"

    def test_comment_line_prefixes(self):
        assert "//" in KotlinLoder.__comment_line_prefixes__

    def test_comment_code_blocks(self):
        assert ("/*", "*/") in KotlinLoder.__comment_code_blocks__

    def test_ignore_dirs(self):
        assert "build" in KotlinLoder.__ignore_dirs__
        assert ".gradle" in KotlinLoder.__ignore_dirs__


class TestCreateItem:
    def test_creates_class_item(self):
        from strictacode.kotlin.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(
            type="class",
            name="UserService",
            lineno=1,
            endline=30,
            complexity=8,
            classname=None,
            methods=[],
            closures=[],
        )
        assert item.type == FileItemTypes.CLASS
        assert item.name == "UserService"

    def test_creates_function_item(self):
        from strictacode.kotlin.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(
            type="function", name="init", lineno=5, endline=10, complexity=2, methods=[], closures=[]
        )
        assert item.type == FileItemTypes.FUNCTION

    def test_creates_method_item(self):
        from strictacode.kotlin.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(
            type="method",
            name="getUser",
            lineno=10,
            endline=20,
            complexity=3,
            classname="UserService",
            methods=[],
            closures=[],
        )
        assert item.type == FileItemTypes.METHOD
        assert item.class_name == "UserService"


def _make_kotlin_collector_json(root):
    """Build Kotlin-collector-like JSON with a real file path under root."""
    src_dir = root / "src"
    src_dir.mkdir()
    filepath = src_dir / "Main.kt"
    filepath.write_text("class App\n")

    return {
        str(filepath): [
            {
                "type": "class",
                "name": "App",
                "lineno": 5,
                "endline": 30,
                "complexity": 4,
                "methods": [
                    {
                        "type": "method",
                        "name": "run",
                        "lineno": 10,
                        "endline": 25,
                        "complexity": 3,
                        "classname": "App",
                        "closures": [],
                    },
                ],
            },
            {
                "type": "function",
                "name": "main",
                "lineno": 35,
                "endline": 40,
                "complexity": 1,
                "closures": [],
            },
        ],
    }


class TestKotlinLoderCollect:
    @patch("strictacode.kotlin.collector.collect")
    def test_collect_returns_file_items(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_kotlin_collector_json(tmp_path)
        loader = KotlinLoder(str(tmp_path))

        result = loader.collect()

        filepath = str(tmp_path / "src" / "Main.kt")
        assert filepath in result
        assert len(result[filepath]) == 2

        from strictacode.loader import FileItemTypes

        assert result[filepath][0].type == FileItemTypes.CLASS
        assert result[filepath][0].name == "App"
        assert result[filepath][1].type == FileItemTypes.FUNCTION
        assert result[filepath][1].name == "main"

    @patch("strictacode.kotlin.collector.collect")
    def test_collect_with_method(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_kotlin_collector_json(tmp_path)
        loader = KotlinLoder(str(tmp_path))
        result = loader.collect()

        filepath = str(tmp_path / "src" / "Main.kt")
        cls_item = result[filepath][0]
        assert len(cls_item.methods) == 1
        assert cls_item.methods[0].name == "run"
        assert cls_item.methods[0].class_name == "App"

    @patch("strictacode.kotlin.collector.collect")
    def test_collect_kotlinc_error_raises(self, mock_collect, tmp_path):
        mock_collect.side_effect = RuntimeError("kotlinc: not found")
        loader = KotlinLoder(str(tmp_path))

        with pytest.raises(RuntimeError, match="kotlinc: not found"):
            loader.collect()


class TestKotlinLoderBuild:
    @patch("strictacode.kotlin.analyzer.analyze")
    @patch("strictacode.kotlin.collector.collect")
    def test_build_adds_graph_nodes(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_kotlin_collector_json(tmp_path)

        src_dir = tmp_path / "src"
        analyzer_data = {
            "nodes": [f"{src_dir}/Main.kt:App", f"{src_dir}/Main.kt:Base"],
            "edges": [
                {"source": f"{src_dir}/Main.kt:App", "target": f"{src_dir}/Main.kt:Base"},
            ],
        }
        mock_analyze.return_value = analyzer_data
        loader = KotlinLoder(str(tmp_path))
        loader.load()

        nodes = loader.sources.graph.nodes
        assert f"{src_dir}/Main.kt:App" in nodes

    @patch("strictacode.kotlin.analyzer.analyze")
    @patch("strictacode.kotlin.collector.collect")
    def test_build_adds_graph_edges(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_kotlin_collector_json(tmp_path)

        src_dir = tmp_path / "src"
        analyzer_data = {
            "nodes": [f"{src_dir}/Main.kt:App", f"{src_dir}/Main.kt:Base"],
            "edges": [
                {"source": f"{src_dir}/Main.kt:App", "target": f"{src_dir}/Main.kt:Base"},
            ],
        }
        mock_analyze.return_value = analyzer_data
        loader = KotlinLoder(str(tmp_path))
        loader.load()

        edges = loader.sources.graph.edges
        assert len(edges) == 1
        assert f"{src_dir}/Main.kt:App" in edges
        assert f"{src_dir}/Main.kt:Base" in edges[f"{src_dir}/Main.kt:App"]

    @patch("strictacode.kotlin.analyzer.analyze")
    @patch("strictacode.kotlin.collector.collect")
    def test_build_empty_analyzer(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_kotlin_collector_json(tmp_path)
        mock_analyze.return_value = {"nodes": [], "edges": []}
        loader = KotlinLoder(str(tmp_path))
        loader.load()

        assert len(loader.sources.graph.nodes) == 0

    @patch("strictacode.kotlin.analyzer.analyze")
    @patch("strictacode.kotlin.collector.collect")
    def test_build_filters_uncollected_nodes(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_kotlin_collector_json(tmp_path)

        src_dir = tmp_path / "src"
        analyzer_data = {
            "nodes": [f"{src_dir}/Main.kt:App", "other.kt:SomeClass"],
            "edges": [
                {"source": f"{src_dir}/Main.kt:App", "target": "other.kt:SomeClass"},
            ],
        }
        mock_analyze.return_value = analyzer_data
        loader = KotlinLoder(str(tmp_path))
        loader.load()

        nodes = loader.sources.graph.nodes
        assert f"{src_dir}/Main.kt:App" in nodes
        assert "other.kt:SomeClass" not in nodes
