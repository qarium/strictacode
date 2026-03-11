from ..loader import Loader, FileItem, FileItemTypes

from . import collector


def _create_item(**kwargs) -> FileItem:
    return FileItem(type=kwargs["type"],
                    name=kwargs["name"],
                    lineno=kwargs["lineno"],
                    endline=kwargs["endline"],
                    complexity=kwargs["complexity"],
                    class_name=kwargs.get("classname"),
                    methods=[_create_item(**i) for i in (kwargs.get("methods") or [])],
                    closures=[_create_item(**i) for i in (kwargs.get("closures") or [])])


class JSLoder(Loader):
    __lang__ = "javascript"
    __ignore_dirs__ = []
    __comment_line_prefixes__ = ["//"]
    __comment_code_blocks__ = [
        ("/*", "*/"),
    ]

    def collect(self) -> dict[str, list[FileItem]]:
        data = collector.collect(self.root)

        metrics = {}

        for filepath, items in data.items():
            if self._should_exclude_file(filepath):
                continue

            if filepath not in metrics:
                metrics[filepath] = []

            metrics[filepath].extend((_create_item(**i) for i in items))
            metrics[filepath].sort(key=lambda i: 0 if i.type == FileItemTypes.CLASS else 1)

        return metrics

    def build(self):
        pass
