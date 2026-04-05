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
    """Check if node and @babel/parser + @babel/traverse are available."""
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
    """Build NODE_PATH env with local and global npm roots."""
    import os
    import sys

    env = os.environ.copy()
    local_root = subprocess.check_output(["npm", "root"], text=True).strip()
    global_root = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    env["NODE_PATH"] = (";" if sys.platform == "win32" else ":").join([local_root, global_root])
    return env


pytestmark = pytest.mark.skipif(
    not _babel_available(),
    reason="requires node with @babel/parser and @babel/traverse",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path, filename, code):
    """Write dedented code to a file and run analysis on the directory."""
    (tmp_path / filename).write_text(textwrap.dedent(code))
    return analyze(str(tmp_path))


def _node_names(result):
    """Return set of node names (strip the file: prefix)."""
    return {n.split(":")[-1] for n in result["nodes"]}


def _edge_pairs(result):
    """Return set of (source_name, target_name) pairs from analysis edges."""
    return {(e["source"].split(":")[-1], e["target"].split(":")[-1]) for e in result["edges"]}


# ===========================================================================
# Tests
# ===========================================================================


class TestClassRelations:
    def test_class_extends(self, tmp_path):
        """Class extends creates inheritance edge."""
        """Class with extends creates an inheritance edge."""
        r = _write(tmp_path, "dog.ts", "class Dog extends Animal {}\n")
        assert "Dog" in _node_names(r)
        edge = (r["edges"] or [None])[0]
        assert edge is not None
        assert edge["source"].endswith(":Dog")
        assert edge["target"].endswith(":Animal")

    def test_class_implements(self, tmp_path):
        """Class implements creates inheritance edge."""
        r = _write(tmp_path, "service.ts", "class MyService implements IService {}\n")
        assert "MyService" in _node_names(r)
        edge = (r["edges"] or [None])[0]
        assert edge is not None
        assert edge["source"].endswith(":MyService")
        assert edge["target"].endswith(":IService")

    def test_class_expression(self, tmp_path):
        """Class expression assigned to const is registered as node."""
        r = _write(tmp_path, "expr.js", "const Router = class {}\n")
        assert "Router" in _node_names(r)

    def test_multiple_classes(self, tmp_path):
        """Multiple classes in one file create correct nodes and edges."""
        r = _write(
            tmp_path,
            "chain.ts",
            """\
            class A {}
            class B extends A {}
            class C extends B {}
        """,
        )
        names = _node_names(r)
        assert names == {"A", "B", "C"}
        assert len(r["edges"]) == 2
        sources = {e["source"].split(":")[-1] for e in r["edges"]}
        targets = {e["target"].split(":")[-1] for e in r["edges"]}
        assert sources == {"B", "C"}
        assert targets == {"A", "B"}


class TestTypeUsageNew:
    def test_new_expression_same_file(self, tmp_path):
        """new X() inside a method creates usage edge."""
        r = _write(
            tmp_path,
            "svc.js",
            """\
            class Request {}
            class Handler {
                create() {
                    return new Request();
                }
            }
            """,
        )
        assert ("Handler", "Request") in _edge_pairs(r)

    def test_new_expression_cross_file(self, tmp_path):
        """new X() with import creates cross-file usage edge."""
        (tmp_path / "core.js").write_text("class Request {}\n")
        (tmp_path / "handler.js").write_text(
            "import { Request } from './core';\n"
            "class Handler {\n"
            "    create() {\n"
            "        return new Request();\n"
            "    }\n"
            "}\n",
        )
        r = analyze(str(tmp_path))
        assert ("Handler", "Request") in _edge_pairs(r)

    def test_new_without_import_no_edge(self, tmp_path):
        """new X() without import and X not declared — no edge."""
        (tmp_path / "svc.js").write_text(
            "class Handler {\n    create() {\n        return new Request();\n    }\n}\n",
        )
        r = analyze(str(tmp_path))
        assert len(r["edges"]) == 0

    def test_lowercase_new_not_captured(self, tmp_path):
        """new lowercase() is not captured as usage."""
        (tmp_path / "svc.js").write_text(
            "class Handler {\n    run() {\n        const x = new Map();\n    }\n}\n",
        )
        r = analyze(str(tmp_path))
        assert len(r["edges"]) == 0


class TestTypeUsageStatic:
    def test_static_method_call(self, tmp_path):
        """X.method() with import creates usage edge."""
        (tmp_path / "log.js").write_text("class Logger {}\n")
        (tmp_path / "svc.js").write_text(
            "import { Logger } from './log';\nclass Service {\n    run() {\n        Logger.info();\n    }\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("Service", "Logger") in _edge_pairs(r)

    def test_static_property_access(self, tmp_path):
        """X.prop with import creates usage edge."""
        (tmp_path / "cfg.js").write_text("class Config {}\n")
        (tmp_path / "svc.js").write_text(
            "import { Config } from './cfg';\n"
            "class Service {\n"
            "    run() {\n"
            "        const t = Config.timeout;\n"
            "    }\n"
            "}\n",
        )
        r = analyze(str(tmp_path))
        assert ("Service", "Config") in _edge_pairs(r)

    def test_namespace_new(self, tmp_path):
        """new Core.X() with namespace import creates edge."""
        (tmp_path / "core.js").write_text("class Request {}\n")
        (tmp_path / "svc.js").write_text(
            "import * as Core from './core';\n"
            "class Service {\n"
            "    run() {\n"
            "        return new Core.Request();\n"
            "    }\n"
            "}\n",
        )
        r = analyze(str(tmp_path))
        assert ("Service", "Request") in _edge_pairs(r)

    def test_namespace_static(self, tmp_path):
        """Core.X.method() with namespace import creates edge."""
        (tmp_path / "log.js").write_text("class Logger {}\n")
        (tmp_path / "svc.js").write_text(
            "import * as Log from './log';\nclass Service {\n    run() {\n        Log.Logger.info();\n    }\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("Service", "Logger") in _edge_pairs(r)


class TestTypeUsageEdgeCases:
    def test_no_self_usage_edge(self, tmp_path):
        """A class using new Self() does not create a self-edge."""
        r = _write(
            tmp_path,
            "node.js",
            """\
            class Node {
                clone() {
                    return new Node();
                }
            }
            """,
        )
        for e in r["edges"]:
            assert e["source"] != e["target"]

    def test_no_duplicate_usage_edge(self, tmp_path):
        """Multiple usages of same type create only one edge."""
        (tmp_path / "core.js").write_text("class Request {}\n")
        (tmp_path / "svc.js").write_text(
            "import { Request } from './core';\n"
            "class Handler {\n"
            "    a() { return new Request(); }\n"
            "    b() { return new Request(); }\n"
            "}\n",
        )
        r = analyze(str(tmp_path))
        handler_req = [e for e in r["edges"] if "Handler" in e["source"] and "Request" in e["target"]]
        assert len(handler_req) == 1

    def test_usage_with_inheritance_combined(self, tmp_path):
        """Usage edges coexist with inheritance edges."""
        (tmp_path / "base.js").write_text("class Base {}\nclass Request {}\n")
        (tmp_path / "derived.js").write_text(
            "import { Base, Request } from './base';\n"
            "class Derived extends Base {\n"
            "    run() { return new Request(); }\n"
            "}\n",
        )
        r = analyze(str(tmp_path))
        pairs = _edge_pairs(r)
        assert ("Derived", "Base") in pairs
        assert ("Derived", "Request") in pairs

    def test_require_destructured_usage(self, tmp_path):
        """const { X } = require('./f') + new X() creates edge."""
        (tmp_path / "core.js").write_text("class Logger {}\n")
        (tmp_path / "app.js").write_text(
            "const { Logger } = require('./core');\n"
            "class App {\n"
            "    start() {\n"
            "        return new Logger();\n"
            "    }\n"
            "}\n",
        )
        r = analyze(str(tmp_path))
        assert ("App", "Logger") in _edge_pairs(r)

    def test_usage_outside_class_via_function(self, tmp_path):
        """new X() inside a function creates usage edge via function call detection."""
        (tmp_path / "core.js").write_text("class Request {}\n")
        (tmp_path / "app.js").write_text(
            "import { Request } from './core';\nfunction main() {\n    return new Request();\n}\n",
        )
        r = analyze(str(tmp_path))
        # Now detected via function call graph: main -> Request
        assert ("main", "Request") in _edge_pairs(r)

    def test_aliased_import(self, tmp_path):
        """import { X as Y } resolves Y to the source file."""
        (tmp_path / "core.js").write_text("class Request {}\n")
        (tmp_path / "svc.js").write_text(
            "import { Request as Req } from './core';\nclass Handler {\n    make() { return new Req(); }\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("Handler", "Request") in _edge_pairs(r)

    def test_external_import_no_edge(self, tmp_path):
        """import from 'lodash' (non-relative) creates no edge."""
        (tmp_path / "svc.js").write_text(
            "import { Something } from 'lodash';\nclass Handler {\n    run() { return new Something(); }\n}\n",
        )
        r = analyze(str(tmp_path))
        assert len(r["edges"]) == 0


class TestImportCollection:
    def test_es_named_import(self, tmp_path):
        """ES named import resolves to target file."""
        (tmp_path / "core.js").write_text("class Request {}\n")
        (tmp_path / "svc.js").write_text("import { Request } from './core';\nclass Service {}\n")
        r = analyze(str(tmp_path))
        # Import data is internal — verify via usage edge in next task
        assert "Service" in _node_names(r)

    def test_require_destructured(self, tmp_path):
        """Destructured require resolves to target file."""
        (tmp_path / "core.js").write_text("class Logger {}\n")
        (tmp_path / "app.js").write_text("const { Logger } = require('./core');\nclass App {}\n")
        r = analyze(str(tmp_path))
        assert "App" in _node_names(r)


class TestFunctionNodes:
    def test_function_declaration_is_node(self, tmp_path):
        """Exported function declaration is registered as a node."""
        r = _write(
            tmp_path,
            "svc.ts",
            """\
            export function validate() {}
            """,
        )
        assert "validate" in _node_names(r)

    def test_arrow_function_is_node(self, tmp_path):
        r = _write(
            tmp_path,
            "svc.ts",
            """\
            export const create = () => {};
            """,
        )
        assert "create" in _node_names(r)

    def test_function_expression_is_node(self, tmp_path):
        r = _write(
            tmp_path,
            "svc.ts",
            """\
            export const handle = function() {};
            """,
        )
        assert "handle" in _node_names(r)

    def test_non_exported_function_is_node(self, tmp_path):
        r = _write(
            tmp_path,
            "svc.ts",
            """\
            function helper() {}
            export function main() {}
            """,
        )
        names = _node_names(r)
        assert "helper" in names
        assert "main" in names


class TestFunctionCalls:
    def test_function_calls_function_same_file(self, tmp_path):
        r = _write(
            tmp_path,
            "svc.ts",
            """\
            export function helper() {}
            export function process() {
                helper();
            }
            """,
        )
        assert ("process", "helper") in _edge_pairs(r)

    def test_function_calls_function_cross_file(self, tmp_path):
        (tmp_path / "a.ts").write_text("export function validate() {}\n")
        (tmp_path / "b.ts").write_text(
            "import { validate } from './a';\nexport function submit() {\n    validate();\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("submit", "validate") in _edge_pairs(r)

    def test_function_calls_class_new(self, tmp_path):
        (tmp_path / "core.ts").write_text("export class Request {}\n")
        (tmp_path / "svc.ts").write_text(
            "import { Request } from './core';\nexport function handle() {\n    return new Request();\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("handle", "Request") in _edge_pairs(r)

    def test_class_method_calls_function(self, tmp_path):
        (tmp_path / "fn.ts").write_text("export function log() {}\n")
        (tmp_path / "cls.ts").write_text(
            "import { log } from './fn';\nexport class Service {\n    run() {\n        log();\n    }\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("Service", "log") in _edge_pairs(r)

    def test_arrow_function_calls_import(self, tmp_path):
        (tmp_path / "a.ts").write_text("export function init() {}\n")
        (tmp_path / "b.ts").write_text(
            "import { init } from './a';\nexport const bootstrap = () => {\n    init();\n};\n",
        )
        r = analyze(str(tmp_path))
        assert ("bootstrap", "init") in _edge_pairs(r)


class TestCallGraphEdgeCases:
    def test_nested_function_calls(self, tmp_path):
        """Calls inside nested functions tracked correctly (stack-based scoping)."""
        r = _write(
            tmp_path,
            "svc.ts",
            """\
            export function helper() {}
            export function outer() {
                function inner() {
                    helper();
                }
                helper();
                helper();
            }
            """,
        )
        pairs = _edge_pairs(r)
        assert ("inner", "helper") in pairs
        assert ("outer", "helper") in pairs

    def test_no_self_edge(self, tmp_path):
        """Recursive call does not create self-edge."""
        r = _write(
            tmp_path,
            "rec.ts",
            """\
            export function factorial(n) {
                return factorial(n - 1);
            }
            """,
        )
        for e in r["edges"]:
            assert e["source"] != e["target"]

    def test_no_duplicate_edge(self, tmp_path):
        """Multiple calls to same target = one edge."""
        (tmp_path / "a.ts").write_text("export function log() {}\n")
        (tmp_path / "b.ts").write_text(
            "import { log } from './a';\nexport function run() {\n    log();\n    log();\n    log();\n}\n",
        )
        r = analyze(str(tmp_path))
        run_log = [e for e in r["edges"] if "run" in e["source"] and "log" in e["target"]]
        assert len(run_log) == 1

    def test_module_level_call_no_edge(self, tmp_path):
        """Call at module level (outside function) creates no edge."""
        (tmp_path / "a.ts").write_text("export function init() {}\n")
        (tmp_path / "b.ts").write_text(
            "import { init } from './a';\ninit();\n",
        )
        r = analyze(str(tmp_path))
        assert len(r["edges"]) == 0

    def test_external_import_no_edge(self, tmp_path):
        """Non-relative import creates no edge."""
        (tmp_path / "svc.ts").write_text(
            "import { debounce } from 'lodash';\nexport function search() {\n    debounce();\n}\n",
        )
        r = analyze(str(tmp_path))
        assert len(r["edges"]) == 0

    def test_namespace_import_call(self, tmp_path):
        """import * as Ns + Ns.x() resolves."""
        (tmp_path / "core.ts").write_text("export function process() {}\n")
        (tmp_path / "svc.ts").write_text(
            "import * as Core from './core';\nexport function run() {\n    Core.process();\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("run", "process") in _edge_pairs(r)

    def test_combined_inheritance_and_calls(self, tmp_path):
        """Inheritance edges + call edges coexist."""
        (tmp_path / "base.ts").write_text(
            "export class Base {}\nexport function init() {}\n",
        )
        (tmp_path / "derived.ts").write_text(
            "import { Base, init } from './base';\n"
            "export class Derived extends Base {\n"
            "    run() {\n"
            "        init();\n"
            "    }\n"
            "}\n",
        )
        r = analyze(str(tmp_path))
        pairs = _edge_pairs(r)
        assert ("Derived", "Base") in pairs
        assert ("Derived", "init") in pairs

    def test_require_destructured_call(self, tmp_path):
        """const { X } = require('./f') + X() creates edge."""
        (tmp_path / "core.js").write_text("function log() {}\n")
        (tmp_path / "app.js").write_text(
            "const { log } = require('./core');\nexport function run() {\n    log();\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("run", "log") in _edge_pairs(r)

    def test_aliased_import_call(self, tmp_path):
        """import { X as Y } + Y() resolves to original name."""
        (tmp_path / "core.ts").write_text("export function isPlainObject() {}\n")
        (tmp_path / "svc.ts").write_text(
            "import { isPlainObject as isPO } from './core';\nexport function validate() {\n    isPO();\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("validate", "isPlainObject") in _edge_pairs(r)


class TestImportResolution:
    def test_require_member_expression_import(self, tmp_path):
        """const X = require('./f').X resolves via MemberExpression parent."""
        (tmp_path / "core.js").write_text("class Logger {}\n")
        (tmp_path / "app.js").write_text(
            "const Logger = require('./core').Logger;\n"
            "class App {\n"
            "    start() {\n"
            "        return new Logger();\n"
            "    }\n"
            "}\n",
        )
        r = analyze(str(tmp_path))
        assert ("App", "Logger") in _edge_pairs(r)

    def test_default_import_resolves(self, tmp_path):
        """import X from './f' — default import resolves to target file."""
        (tmp_path / "core.js").write_text("class Request {}\n")
        (tmp_path / "svc.js").write_text(
            "import Request from './core';\nclass Handler {\n    make() { return new Request(); }\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("Handler", "Request") in _edge_pairs(r)

    def test_index_file_resolution(self, tmp_path):
        """import { X } from './dir' resolves via dir/index.js."""
        dir_path = tmp_path / "utils"
        dir_path.mkdir()
        (dir_path / "index.js").write_text("class Helper {}\n")
        (tmp_path / "svc.js").write_text(
            "import { Helper } from './utils';\nclass Service {\n    run() { return new Helper(); }\n}\n",
        )
        r = analyze(str(tmp_path))
        assert ("Service", "Helper") in _edge_pairs(r)


class TestArrowInClassCalls:
    def test_arrow_in_class_calls_same_file(self, tmp_path):
        """Arrow function inside a class method tracks call chain through nested scope."""
        r = _write(
            tmp_path,
            "svc.js",
            """\
            function helper() {}
            class Service {
                run() {
                    const fn = () => { helper(); };
                    fn();
                }
            }
            """,
        )
        pairs = _edge_pairs(r)
        # Arrow fn creates a separate node — edges go Service→fn and fn→helper
        assert ("fn", "helper") in pairs
        assert ("Service", "fn") in pairs


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
