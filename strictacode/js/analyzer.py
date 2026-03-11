"""
const fs = require("fs");
const path = require("path");
const parser = require("@babel/parser");
const traverse = require("@babel/traverse").default;

/* ==============================
   CONFIG
============================== */
const IGNORED_DIRECTORIES = ["node_modules", ".git", "dist", "build"];
const IGNORED_FILE_PREFIXES = ["test"];
const IGNORED_FILE_SUFFIXES = [
  ".test.js", ".spec.js",
  ".test.ts", ".spec.ts",
  ".test.jsx", ".spec.jsx",
  ".test.tsx", ".spec.tsx"
];
const ALLOWED_EXTENSIONS = [".js", ".ts", ".jsx", ".tsx"];

/* ==============================
   CLI
============================== */
const inputPath = process.argv[2];
if (!inputPath) {
  console.error("Usage: node script.js <path-to-analyze>");
  process.exit(1);
}
const ROOT_PATH = path.resolve(inputPath);

/* ==============================
   UTILS
============================== */
function shouldIgnoreFile(filePath) {
  const base = path.basename(filePath);
  if (!ALLOWED_EXTENSIONS.includes(path.extname(base))) return true;
  if (IGNORED_FILE_PREFIXES.some(p => base.startsWith(p))) return true;
  if (IGNORED_FILE_SUFFIXES.some(s => base.endsWith(s))) return true;
  return false;
}
function shouldIgnoreDirectory(dirPath) {
  return IGNORED_DIRECTORIES.includes(path.basename(dirPath));
}
function collectFiles(dir) {
  let results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!shouldIgnoreDirectory(fullPath)) {
        results = results.concat(collectFiles(fullPath));
      }
    } else {
      if (!shouldIgnoreFile(fullPath)) results.push(fullPath);
    }
  }
  return results;
}
function getClassName(node, path) {
  if (node.id?.name) return node.id.name;
  const parent = path.parent;
  if (parent.type === "VariableDeclarator" && parent.id.name) return parent.id.name;
  if (parent.type === "AssignmentExpression" && parent.left.name) return parent.left.name;
  return null;
}
function getSuperName(node) {
  if (node.superClass) {
    if (node.superClass.name) return node.superClass.name;
    if (node.superClass.expression?.name) return node.superClass.expression.name;
  }
  return null;
}

/* ==============================
   ANALYZER
============================== */
const nodes = new Set();
const edges = [];

function analyzeFile(filePath) {
  const code = fs.readFileSync(filePath, "utf8");
  let ast;
  try {
    ast = parser.parse(code, {
      sourceType: "unambiguous",
      plugins: [
        "typescript", "jsx",
        "classProperties", "dynamicImport",
        "optionalChaining", "nullishCoalescingOperator"
      ]
    });
  } catch {
    return;
  }

  const rel = path.relative(ROOT_PATH, filePath).split(path.sep).join("/");

  traverse(ast, {
    ClassDeclaration(path) {
      handleClass(path.node, path, rel);
    },
    ClassExpression(path) {
      handleClass(path.node, path, rel);
    },
    TSInterfaceDeclaration(path) {
      const name = path.node.id?.name;
      if (name) {
        nodes.add(`${rel}:${name}`);
      }
      // Interface extends
      if (path.node.extends) {
        for (const ext of path.node.extends) {
          const extName = ext.expression?.name;
          if (extName) {
            edges.push({
              source: `${rel}:${name}`,
              target: `${rel}:${extName}`
            });
          }
        }
      }
    }
  });
}

function handleClass(node, path, rel) {
  const className = getClassName(node, path);
  if (!className) return;

  const nodeKey = `${rel}:${className}`;
  nodes.add(nodeKey);

  // extends
  const superName = getSuperName(node);
  if (superName) {
    edges.push({
      source: nodeKey,
      target: `${rel}:${superName}`
    });
  }

  // implements (TypeScript)
  if (node.implements) {
    for (const impl of node.implements) {
      const implName = impl.expression?.name;
      if (implName) {
        edges.push({
          source: nodeKey,
          target: `${rel}:${implName}`
        });
      }
    }
  }
}

/* ==============================
   MAIN
============================== */
const files = collectFiles(ROOT_PATH);

for (const file of files) {
  analyzeFile(file);
}

const output = {
  nodes: Array.from(nodes),
  edges: edges
};

console.log(JSON.stringify(output, null, 2));
"""

import os
import sys
import json
import tempfile
import subprocess


def analyze(path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        js_file = os.path.join(tmpdir, "analyzer.js")
        with open(js_file, "w") as f:
            f.write(__doc__)

        npm_local_root = subprocess.check_output(["npm", "root"], text=True)
        npm_global_root = subprocess.check_output(["npm", "root", "-g"], text=True)

        env = os.environ.copy()
        env["NODE_PATH"] = (";" if sys.platform == "win32" else ":").join(
            [npm_local_root.strip(), npm_global_root.strip()],
        )

        cmd = ["node", js_file, path]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode != 0:
        if '@babel' in result.stderr:
            result.stderr = result.stderr + '\nTry to install:\n' \
                                            '  * npm install @babel/parser\n' \
                                            '  * npm install @babel/traverse'
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)