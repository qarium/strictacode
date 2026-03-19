import os

from ..loader import Loader, FileItem, FileItemTypes

from . import collector
from . import analyzer


def _create_item(**kwargs) -> FileItem:
    item_type = "class" if kwargs["type"] == "structure" else kwargs["type"]

    return FileItem(type=item_type,
                    name=kwargs["name"],
                    lineno=kwargs["lineno"],
                    endline=kwargs["endline"],
                    complexity=kwargs["complexity"],
                    class_name=kwargs.get("structure"),
                    methods=[_create_item(**i) for i in (kwargs.get("methods") or [])],
                    closures=[_create_item(**i) for i in (kwargs.get("closures") or [])])


class GoLoder(Loader):
    __lang__ = "golang"
    __ignore_dirs__ = []
    __comment_line_prefixes__ = ["//"]
    __comment_code_blocks__ = [
        ("/*", "*/"),
    ]

    def collect(self) -> dict[str, list[FileItem]]:
        data = collector.collect(self.root)

        metrics = {}

        for filepath, items in data.items():
            if filepath not in metrics:
                metrics[filepath] = []

            metrics[filepath].extend((_create_item(**i) for i in items))
            metrics[filepath].sort(key=lambda i: 0 if i.type == FileItemTypes.CLASS else 1)

        return metrics

    def build(self):
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
