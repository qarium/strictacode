import sys
import json
import subprocess

from ..loader import Loader, MetricItem


def _create_item(**kwargs) -> MetricItem:
    return MetricItem(type=kwargs["type"],
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
    __comment_line_prefixes__ = ["#", "\"\"\""]

    def extract_metrics(self) -> dict[str, list[MetricItem]]:
        cmd = [sys.executable, "-m", "radon", "cc", "-j", self.root]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        data = json.loads(result.stdout)

        metrics = {}

        for filepath, items in data.items():
            if self._should_exclude_file(filepath):
                continue

            if filepath not in metrics:
                metrics[filepath] = []

            metrics[filepath].extend((_create_item(**i) for i in items))
            metrics[filepath].sort(key=lambda i: 0 if i.type == "class" else 1)

        return metrics
