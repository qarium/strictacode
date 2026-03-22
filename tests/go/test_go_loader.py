from unittest.mock import patch, MagicMock

import pytest

from strictacode.go.loader import GoLoder


# ---------------------------------------------------------------------------
# GoLoder class attributes
# ---------------------------------------------------------------------------


class TestGoLoaderAttributes:
    def test_lang(self):
        assert GoLoder.__lang__ == "golang"

    def test_comment_line_prefixes(self):
        assert "//" in GoLoder.__comment_line_prefixes__

    def test_comment_code_blocks(self):
        assert ("/*", "*/") in GoLoder.__comment_code_blocks__

    def test_ignore_dirs(self):
        assert GoLoder.__ignore_dirs__ == []


# ---------------------------------------------------------------------------
# _create_item — maps "structure" → "class"
# ---------------------------------------------------------------------------


class TestCreateItem:
    def test_maps_structure_to_class(self):
        from strictacode.go.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(type="structure", name="User", lineno=1, endline=20,
                            complexity=5, methods=[], closures=[])
        assert item.type == FileItemTypes.CLASS
        assert item.name == "User"

    def test_keeps_function_type(self):
        from strictacode.go.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(type="function", name="main", lineno=1, endline=10,
                            complexity=1, methods=[], closures=[])
        assert item.type == FileItemTypes.FUNCTION

    def test_maps_method_with_structure(self):
        from strictacode.go.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(type="method", name="GetName", lineno=5, endline=10,
                            complexity=1, structure="User", methods=[], closures=[])
        assert item.type == FileItemTypes.METHOD
        assert item.class_name == "User"


# ---------------------------------------------------------------------------
# collector.collect — mock subprocess
# ---------------------------------------------------------------------------


def _make_go_collector_json(root):
    """Build go-collector-like JSON with a real file path under root."""
    cmd_dir = root / "cmd"
    cmd_dir.mkdir()
    filepath = cmd_dir / "main.go"
    filepath.write_text("package main\n")

    return {
        str(filepath): [
            {
                "type": "structure",
                "name": "App",
                "lineno": 10,
                "endline": 30,
                "complexity": 4,
                "methods": [
                    {
                        "type": "method",
                        "name": "Run",
                        "lineno": 15,
                        "endline": 25,
                        "complexity": 3,
                        "structure": "App",
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


class TestGoLoaderCollect:
    @patch("strictacode.go.collector.collect")
    def test_collect_returns_file_items(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_go_collector_json(tmp_path)
        loader = GoLoder(str(tmp_path))

        result = loader.collect()

        filepath = str(tmp_path / "cmd" / "main.go")
        assert filepath in result
        assert len(result[filepath]) == 2

        from strictacode.loader import FileItemTypes
        assert result[filepath][0].type == FileItemTypes.CLASS
        assert result[filepath][0].name == "App"
        assert result[filepath][1].type == FileItemTypes.FUNCTION
        assert result[filepath][1].name == "main"

    @patch("strictacode.go.collector.collect")
    def test_collect_with_method(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_go_collector_json(tmp_path)
        loader = GoLoder(str(tmp_path))
        result = loader.collect()

        filepath = str(tmp_path / "cmd" / "main.go")
        cls_item = result[filepath][0]
        assert len(cls_item.methods) == 1
        assert cls_item.methods[0].name == "Run"
        assert cls_item.methods[0].class_name == "App"

    @patch("strictacode.go.collector.collect")
    def test_collect_go_error_raises(self, mock_collect, tmp_path):
        mock_collect.side_effect = RuntimeError("go: not found")
        loader = GoLoder(str(tmp_path))

        with pytest.raises(RuntimeError, match="go: not found"):
            loader.collect()


# ---------------------------------------------------------------------------
# analyzer.analyze — mock subprocess
# ---------------------------------------------------------------------------


class TestGoLoaderBuild:
    @patch("strictacode.go.analyzer.analyze")
    @patch("strictacode.go.collector.collect")
    def test_build_adds_graph_nodes(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_go_collector_json(tmp_path)

        cmd_dir = tmp_path / "cmd"
        analyzer_data = {
            "nodes": [f"{cmd_dir}/main.go:App", f"{cmd_dir}/main.go:Handler"],
            "edges": [
                {"source": f"{cmd_dir}/main.go:Handler", "target": f"{cmd_dir}/main.go:App"},
            ],
        }
        mock_analyze.return_value = analyzer_data
        loader = GoLoder(str(tmp_path))
        loader.load()

        nodes = loader.sources.graph.nodes
        assert f"{cmd_dir}/main.go:App" in nodes

    @patch("strictacode.go.analyzer.analyze")
    @patch("strictacode.go.collector.collect")
    def test_build_adds_graph_edges(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_go_collector_json(tmp_path)

        cmd_dir = tmp_path / "cmd"
        analyzer_data = {
            "nodes": [f"{cmd_dir}/main.go:App", f"{cmd_dir}/main.go:Handler"],
            "edges": [
                {"source": f"{cmd_dir}/main.go:Handler", "target": f"{cmd_dir}/main.go:App"},
            ],
        }
        mock_analyze.return_value = analyzer_data
        loader = GoLoder(str(tmp_path))
        loader.load()

        edges = loader.sources.graph.edges
        assert len(edges) == 1
        assert f"{cmd_dir}/main.go:Handler" in edges
        assert f"{cmd_dir}/main.go:App" in edges[f"{cmd_dir}/main.go:Handler"]

    @patch("strictacode.go.analyzer.analyze")
    @patch("strictacode.go.collector.collect")
    def test_build_empty_analyzer(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_go_collector_json(tmp_path)
        mock_analyze.return_value = {"nodes": [], "edges": []}
        loader = GoLoder(str(tmp_path))
        loader.load()

        assert len(loader.sources.graph.nodes) == 0

    @patch("strictacode.go.analyzer.analyze")
    @patch("strictacode.go.collector.collect")
    def test_build_filters_uncollected_nodes(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_go_collector_json(tmp_path)

        cmd_dir = tmp_path / "cmd"
        analyzer_data = {
            "nodes": [f"{cmd_dir}/main.go:App", "other.go:SomeClass"],
            "edges": [
                {"source": f"{cmd_dir}/main.go:App", "target": "other.go:SomeClass"},
            ],
        }
        mock_analyze.return_value = analyzer_data
        loader = GoLoder(str(tmp_path))
        loader.load()

        nodes = loader.sources.graph.nodes
        assert f"{cmd_dir}/main.go:App" in nodes
        assert "other.go:SomeClass" not in nodes
