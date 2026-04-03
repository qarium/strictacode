from __future__ import annotations

import os
import typing as t

from ..loader import FileItem, FileItemTypes, Loader
from . import analyzer, collector


def _create_item(**kwargs: t.Any) -> FileItem:
    """Create a FileItem from a dictionary, recursing into methods and closures.

    Args:
        **kwargs: Dictionary with keys ``type``, ``name``, ``lineno``,
            ``endline``, ``complexity``, ``classname``, ``methods``,
            ``closures``.

    Returns:
        Populated FileItem instance.
    """
    return FileItem(
        type=kwargs["type"],
        name=kwargs["name"],
        lineno=kwargs.get("lineno", 0),
        endline=kwargs.get("endline", 0),
        complexity=kwargs.get("complexity", 0),
        class_name=kwargs.get("classname"),
        methods=[_create_item(**i) for i in (kwargs.get("methods") or [])],
        closures=[_create_item(**i) for i in (kwargs.get("closures") or [])],
    )


class SwiftLoder(Loader):
    """Loader implementation for Swift source code analysis."""

    __lang__ = "swift"
    __ignore_dirs__: t.ClassVar[list[str]] = ["build", ".build", ".swiftpm", "DerivedData", "Packages"]
    __comment_line_prefixes__: t.ClassVar[list[str]] = ["//", "///"]
    __comment_code_blocks__: t.ClassVar[list[tuple[str, str]]] = [("/*", "*/"), ("/**", "*/")]

    def collect(self) -> dict[str, list[FileItem]]:
        """Collect Swift source metrics using the collector module.

        Returns:
            Mapping of file paths to lists of FileItem instances,
            sorted with classes before functions.
        """
        data = collector.collect(self.root)
        metrics: dict[str, list[FileItem]] = {}

        for filepath, items in data.items():
            if filepath not in metrics:
                metrics[filepath] = []

            metrics[filepath].extend(_create_item(**i) for i in items)
            metrics[filepath].sort(key=lambda i: 0 if i.type == FileItemTypes.CLASS else 1)

        return metrics

    def build(self) -> None:
        """Build the inheritance graph using the analyzer module.

        Only nodes and edges referencing collected module paths
        are added to the graph.
        """
        data = analyzer.analyze(self.root)
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        collected_paths = {os.path.abspath(m.path) for m in self.sources.modules}

        for node in nodes:
            filepath = os.path.abspath(node.split(":")[0])

            if filepath in collected_paths:
                self.sources.graph.add_node(node)

        for edge in edges:
            source_path = os.path.abspath(edge["source"].split(":")[0])
            target_path = os.path.abspath(edge["target"].split(":")[0])

            if source_path in collected_paths and target_path in collected_paths:
                self.sources.graph.add_edge(edge["source"], edge["target"])
