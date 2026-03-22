"""Integration tests for JS analyzer — runs real node + babel on temp JS/TS files."""

import shutil
import subprocess
import textwrap

import pytest
from strictacode.js.analyzer import analyze

# ---------------------------------------------------------------------------
# Skip when node or babel is not available
# ---------------------------------------------------------------------------


def _babel_available():
    if shutil.which("node") is None:
        return False
    try:
        result = subprocess.run(
            ["node", "-e", "require('@babel/parser'); require('@babel/traverse')"],
            capture_output=True,
            text=True,
            env=_node_env(),
        )
        return result.returncode == 0
    except Exception:
        return False


def _node_env():
    import os
    import sys

    env = os.environ.copy()
    local_root = subprocess.check_output(["npm", "root"], text=True).strip()
    global_root = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    env["NODE_PATH"] = (";" if sys.platform == "win32" else ":").join(
        [local_root, global_root]
    )
    return env


pytestmark = pytest.mark.skipif(
    not _babel_available(),
    reason="requires node with @babel/parser and @babel/traverse",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path, filename, code):
    (tmp_path / filename).write_text(textwrap.dedent(code))
    return analyze(str(tmp_path))


def _node_names(result):
    """Return set of node names (strip the file: prefix)."""
    return {n.split(":")[-1] for n in result["nodes"]}


# ===========================================================================
# Tests
# ===========================================================================


class TestClassRelations:
    def test_class_extends(self, tmp_path):
        r = _write(tmp_path, "dog.ts", "class Dog extends Animal {}\n")
        assert "Dog" in _node_names(r)
        edge = (r["edges"] or [None])[0]
        assert edge is not None
        assert edge["source"].endswith(":Dog")
        assert edge["target"].endswith(":Animal")

    def test_class_implements(self, tmp_path):
        r = _write(tmp_path, "service.ts", "class MyService implements IService {}\n")
        assert "MyService" in _node_names(r)
        edge = (r["edges"] or [None])[0]
        assert edge is not None
        assert edge["source"].endswith(":MyService")
        assert edge["target"].endswith(":IService")

    def test_class_expression(self, tmp_path):
        r = _write(tmp_path, "expr.js", "const Router = class {}\n")
        assert "Router" in _node_names(r)

    def test_multiple_classes(self, tmp_path):
        r = _write(tmp_path, "chain.ts", """\
            class A {}
            class B extends A {}
            class C extends B {}
        """)
        names = _node_names(r)
        assert names == {"A", "B", "C"}
        assert len(r["edges"]) == 2
        sources = {e["source"].split(":")[-1] for e in r["edges"]}
        targets = {e["target"].split(":")[-1] for e in r["edges"]}
        assert sources == {"B", "C"}
        assert targets == {"A", "B"}


class TestInterfaceRelations:
    def test_interface_node(self, tmp_path):
        r = _write(tmp_path, "iface.ts", "interface Runnable {}\n")
        assert "Runnable" in _node_names(r)
        assert len(r["edges"]) == 0

    def test_interface_extends(self, tmp_path):
        r = _write(tmp_path, "derived.ts", "interface Derived extends Base {}\n")
        assert "Derived" in _node_names(r)
        edge = (r["edges"] or [None])[0]
        assert edge is not None
        assert edge["source"].endswith(":Derived")
        assert edge["target"].endswith(":Base")
