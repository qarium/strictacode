import os
import json
import tempfile
import subprocess

from ..loader import Loader, MetricItem

from . import constants


def _create_item(**kwargs) -> MetricItem:
    item_type = "class" if kwargs["type"] == "structure" else kwargs["type"]

    return MetricItem(type=item_type,
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
    __comment_line_prefixes__ = ["//", "/*", "*/"]

    def extract_metrics(self) -> dict[str, list[MetricItem]]:
        with tempfile.TemporaryDirectory() as tmpdir:
            go_file = os.path.join(tmpdir, "metrics.go")
            with open(go_file, "w") as f:
                f.write(constants.ANALYZE_SCRIPT)

            cmd = ["go", "run", go_file, self.root]
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        data = json.loads(result.stdout)

        metrics = {}

        for filepath, items in data.items():
            if self._should_exclude_file(filepath) or '/gen' in filepath:
                continue

            if filepath not in metrics:
                metrics[filepath] = []

            metrics[filepath].extend((_create_item(**i) for i in items))
            metrics[filepath].sort(key=lambda i: 0 if i.type == "class" else 1)

        return metrics
