import sys
import json
import subprocess
from collections import defaultdict

from ..loader import Loader, FileItem, FileItemTypes

from .analyzer import Analyzer


def _create_item(**kwargs) -> FileItem:
    return FileItem(type=kwargs["type"],
                    name=kwargs["name"],
                    lineno=kwargs["lineno"],
                    endline=kwargs["endline"],
                    complexity=kwargs["complexity"],
                    class_name=kwargs.get("classname"),
                    methods=[_create_item(**i) for i in (kwargs.get("methods") or [])],
                    closures=[_create_item(**i) for i in (kwargs.get("closures") or [])])


class PyLoder(Loader):
    __lang__ = "python"
    __ignore_dirs__ = [
        ".venv", "venv",
        ".env", "env",
    ]
    __comment_line_prefixes__ = ["#"]
    __comment_code_blocks__ = [
        ("'''", "'''"),
        ("\"\"\"", "\"\"\""),
    ]

    def collect(self) -> dict[str, list[FileItem]]:
        cmd = [sys.executable, "-m", "radon", "cc", "-j", self.root]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        data = json.loads(result.stdout)

        file_to_items = {}

        for filepath, items in data.items():
            if self._should_exclude_file(filepath):
                continue

            if filepath not in file_to_items:
                file_to_items[filepath] = []

            file_to_items[filepath].extend((_create_item(**i) for i in items))
            file_to_items[filepath].sort(key=lambda i: 0 if i.type == FileItemTypes.CLASS else 1)

        return file_to_items

    def build(self):
        class_methods = {}
        class_bases = defaultdict(list)

        for module in self.sources.modules:
            analyzer = Analyzer.file(module.path)

            if not analyzer:
                continue

            for cls in analyzer.classes:
                class_methods[cls] = analyzer.classes[cls]

            for cls, bases in analyzer.class_bases.items():
                class_bases[cls].extend(bases)

        for cls in class_methods:
            self.sources.graph.add_node(cls)

        for cls, bases in class_bases.items():
            for base in bases:
                self.sources.graph.add_edge(cls, base)
