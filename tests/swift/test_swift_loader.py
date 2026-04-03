from unittest.mock import patch

import pytest
from strictacode.swift.loader import SwiftLoder


class TestSwiftLoderAttributes:
    def test_lang(self):
        assert SwiftLoder.__lang__ == "swift"

    def test_comment_line_prefixes(self):
        assert "//" in SwiftLoder.__comment_line_prefixes__
        assert "///" in SwiftLoder.__comment_line_prefixes__

    def test_comment_code_blocks(self):
        assert ("/*", "*/") in SwiftLoder.__comment_code_blocks__
        assert ("/**", "*/") in SwiftLoder.__comment_code_blocks__

    def test_ignore_dirs(self):
        assert ".build" in SwiftLoder.__ignore_dirs__
        assert ".swiftpm" in SwiftLoder.__ignore_dirs__
        assert "DerivedData" in SwiftLoder.__ignore_dirs__
        assert "Packages" in SwiftLoder.__ignore_dirs__


class TestCreateItem:
    def test_creates_class_item(self):
        from strictacode.loader import FileItemTypes
        from strictacode.swift.loader import _create_item

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
        from strictacode.loader import FileItemTypes
        from strictacode.swift.loader import _create_item

        item = _create_item(type="function", name="init", lineno=5, endline=10, complexity=2, methods=[], closures=[])
        assert item.type == FileItemTypes.FUNCTION

    def test_creates_method_item(self):
        from strictacode.loader import FileItemTypes
        from strictacode.swift.loader import _create_item

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


def _make_swift_collector_json(root):
    src_dir = root / "Sources"
    src_dir.mkdir()
    filepath = src_dir / "Main.swift"
    filepath.write_text("struct App {}\n")
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


class TestSwiftLoderCollect:
    @patch("strictacode.swift.collector.collect")
    def test_collect_returns_file_items(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_swift_collector_json(tmp_path)
        loader = SwiftLoder(str(tmp_path))
        result = loader.collect()

        filepath = str(tmp_path / "Sources" / "Main.swift")
        from strictacode.loader import FileItemTypes

        assert filepath in result
        assert len(result[filepath]) == 2
        assert result[filepath][0].type == FileItemTypes.CLASS
        assert result[filepath][1].type == FileItemTypes.FUNCTION

    @patch("strictacode.swift.collector.collect")
    def test_collect_with_method(self, mock_collect, tmp_path):
        mock_collect.return_value = _make_swift_collector_json(tmp_path)
        loader = SwiftLoder(str(tmp_path))
        result = loader.collect()

        filepath = str(tmp_path / "Sources" / "Main.swift")
        assert len(result[filepath][0].methods) == 1
        assert result[filepath][0].methods[0].name == "run"

    @patch("strictacode.swift.collector.collect")
    def test_collect_swift_error_raises(self, mock_collect, tmp_path):
        mock_collect.side_effect = RuntimeError("swift: not found")
        loader = SwiftLoder(str(tmp_path))
        with pytest.raises(RuntimeError, match="swift: not found"):
            loader.collect()


class TestSwiftLoderBuild:
    @patch("strictacode.swift.analyzer.analyze")
    @patch("strictacode.swift.collector.collect")
    def test_build_adds_graph_nodes(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_swift_collector_json(tmp_path)
        src_dir = tmp_path / "Sources"
        mock_analyze.return_value = {
            "nodes": [f"{src_dir}/Main.swift:App", f"{src_dir}/Main.swift:Base"],
            "edges": [{"source": f"{src_dir}/Main.swift:App", "target": f"{src_dir}/Main.swift:Base"}],
        }
        loader = SwiftLoder(str(tmp_path))
        loader.load()
        assert f"{src_dir}/Main.swift:App" in loader.sources.graph.nodes

    @patch("strictacode.swift.analyzer.analyze")
    @patch("strictacode.swift.collector.collect")
    def test_build_adds_graph_edges(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_swift_collector_json(tmp_path)
        src_dir = tmp_path / "Sources"
        mock_analyze.return_value = {
            "nodes": [f"{src_dir}/Main.swift:App", f"{src_dir}/Main.swift:Base"],
            "edges": [{"source": f"{src_dir}/Main.swift:App", "target": f"{src_dir}/Main.swift:Base"}],
        }
        loader = SwiftLoder(str(tmp_path))
        loader.load()
        edges = loader.sources.graph.edges
        assert len(edges) == 1

    @patch("strictacode.swift.analyzer.analyze")
    @patch("strictacode.swift.collector.collect")
    def test_build_empty_analyzer(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_swift_collector_json(tmp_path)
        mock_analyze.return_value = {"nodes": [], "edges": []}
        loader = SwiftLoder(str(tmp_path))
        loader.load()
        assert len(loader.sources.graph.nodes) == 0

    @patch("strictacode.swift.analyzer.analyze")
    @patch("strictacode.swift.collector.collect")
    def test_build_filters_uncollected_nodes(self, mock_collect, mock_analyze, tmp_path):
        mock_collect.return_value = _make_swift_collector_json(tmp_path)
        src_dir = tmp_path / "Sources"
        mock_analyze.return_value = {
            "nodes": [f"{src_dir}/Main.swift:App", "other.swift:SomeClass"],
            "edges": [{"source": f"{src_dir}/Main.swift:App", "target": "other.swift:SomeClass"}],
        }
        loader = SwiftLoder(str(tmp_path))
        loader.load()
        nodes = loader.sources.graph.nodes
        assert f"{src_dir}/Main.swift:App" in nodes
        assert "other.swift:SomeClass" not in nodes
