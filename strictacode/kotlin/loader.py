import os

from ..loader import FileItem, FileItemTypes, Loader
from . import analyzer, collector


def _create_item(**kwargs) -> FileItem:
    """Recursively build a FileItem from a raw metric dictionary.

    Args:
        **kwargs: Metric fields (type, name, lineno, endline, complexity,
            classname, methods, closures).

    Returns:
        Populated FileItem instance.
    """
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


class KotlinLoder(Loader):
    __lang__ = "kotlin"
    __ignore_dirs__ = ["build", ".gradle"]
    __comment_line_prefixes__ = ["//"]
    __comment_code_blocks__ = [
        ("/*", "*/"),
    ]

    def collect(self) -> dict[str, list[FileItem]]:
        """Collect metrics from Kotlin source files.

        Returns:
            Mapping of relative file paths to lists of FileItem instances,
            sorted with classes before functions.
        """
        data = collector.collect(self.root)

        metrics = {}

        for filepath, items in data.items():
            if filepath not in metrics:
                metrics[filepath] = []

            metrics[filepath].extend(_create_item(**i) for i in items)
            metrics[filepath].sort(key=lambda i: 0 if i.type == FileItemTypes.CLASS else 1)

        return metrics

    def build(self):
        """Build the inheritance graph from analyzer output.

        Adds nodes and edges for types whose source files are among
        the collected modules.
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
