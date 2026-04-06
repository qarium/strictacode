import os

from ..loader import FileItem, FileItemTypes, Loader
from . import analyzer, collector


def _create_item(**kwargs) -> FileItem:
    return FileItem(
        type=kwargs["type"],
        name=kwargs["name"],
        lineno=kwargs["lineno"],
        endline=kwargs["endline"],
        complexity=kwargs["complexity"],
        class_name=kwargs.get("classname"),
        methods=[_create_item(**i) for i in (kwargs.get("methods") or [])],
        closures=[_create_item(**i) for i in (kwargs.get("closures") or [])],
    )


class JSLoder(Loader):
    """Loader implementation for JavaScript source code."""
    __lang__ = "javascript"
    __ignore_dirs__ = []
    __comment_line_prefixes__ = ["//"]
    __comment_code_blocks__ = [
        ("/*", "*/"),
    ]

    def collect(self) -> dict[str, list[FileItem]]:
        """Collect JavaScript file metrics grouped by filepath.

        Returns:
            Mapping of filepath to a list of FileItem with classes
            sorted before other items.
        """
        data = collector.collect(self.root)

        metrics = {}

        for filepath, items in data.items():
            if filepath not in metrics:
                metrics[filepath] = []

            metrics[filepath].extend(_create_item(**i) for i in items)
            metrics[filepath].sort(key=lambda i: 0 if i.type == FileItemTypes.CLASS else 1)

        return metrics

    def build(self) -> None:
        """Build dependency graph from JavaScript module analysis.

        Adds nodes and edges to the sources graph, filtered to only
        modules that were previously collected.
        """
        data = analyzer.analyze(self.root)
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        # Use only modules that were collected
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
