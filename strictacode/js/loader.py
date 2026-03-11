import os
import sys
import json
import tempfile
import subprocess

from ..loader import Loader, FileItem

from . import constants


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
        with tempfile.TemporaryDirectory() as tmpdir:
            js_file = os.path.join(tmpdir, "metrics.js")
            with open(js_file, "w") as f:
                f.write(constants.ANALYZE_SCRIPT)

            npm_local_root = subprocess.check_output(["npm", "root"], text=True)
            npm_global_root = subprocess.check_output(["npm", "root", "-g"], text=True)

            env = os.environ.copy()
            env["NODE_PATH"] = (";" if sys.platform == "win32" else ":").join(
                [npm_local_root.strip(), npm_global_root.strip()],
            )

            cmd = ["node", js_file, self.root]
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            if '@babel' in result.stderr:
                result.stderr = result.stderr + '\nTry to install:\n' \
                                                '  * npm install @babel/parser\n' \
                                                '  * npm install @babel/traverse'
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

    def build(self):
        pass
