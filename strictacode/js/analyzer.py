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

const PARSER_OPTIONS = {
  sourceType: "unambiguous",
  plugins: [
    "typescript", "jsx",
    "classProperties", "dynamicImport",
    "optionalChaining", "nullishCoalescingOperator"
  ]
};

function parseFile(filePath) {
    const code = fs.readFileSync(filePath, "utf8");
    try {
        return parser.parse(code, PARSER_OPTIONS);
    } catch {
        return null;
    }
}

/* ==============================
   ANALYZER
============================== */
const nodes = new Set();
const edges = [];

function analyzeFile(ast, rel) {
  if (!ast) return;

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
    },
    FunctionDeclaration(path) {
      const name = path.node.id?.name;
      if (name) {
        nodes.add(`${rel}:${name}`);
      }
    },
    VariableDeclarator(path) {
      const name = path.node.id?.name;
      if (!name) return;
      const init = path.node.init;
      if (init && (init.type === "FunctionExpression" || init.type === "ArrowFunctionExpression")) {
        nodes.add(`${rel}:${name}`);
      }
    },
  });
}

/* ==============================
   IMPORT COLLECTION
============================== */
const importMap = {}; // file -> { localName -> { targetRel, originalName } }

function resolveImportPath(source, fromRel) {
    if (!source.startsWith(".")) return null;

    const fromDir = path.dirname(fromRel);
    const rawTarget = path.normalize(path.join(fromDir, source));
    let targetRel = rawTarget.split(path.sep).join("/");

    for (const ext of ALLOWED_EXTENSIONS) {
        const candidate = targetRel + ext;
        const fullPath = path.join(ROOT_PATH, candidate);
        if (fs.existsSync(fullPath)) return candidate;
    }

    for (const ext of ALLOWED_EXTENSIONS) {
        const candidate = targetRel + "/index" + ext;
        const fullPath = path.join(ROOT_PATH, candidate);
        if (fs.existsSync(fullPath)) return candidate;
    }

    return null;
}

function collectImports(ast, rel) {
    if (!ast) return;

    const localMap = {};

    traverse(ast, {
        ImportDeclaration(path) {
            const source = path.node.source.value;
            const targetRel = resolveImportPath(source, rel);
            if (!targetRel) return;

            for (const spec of path.node.specifiers) {
                if (spec.type === "ImportSpecifier") {
                    localMap[spec.local.name] = { targetRel, originalName: spec.imported.name };
                } else {
                    localMap[spec.local.name] = { targetRel, originalName: spec.local.name };
                }
            }
        },
        CallExpression(path) {
            if (
                path.node.callee.type === "Identifier" &&
                path.node.callee.name === "require" &&
                path.node.arguments.length === 1 &&
                path.node.arguments[0].type === "StringLiteral"
            ) {
                const source = path.node.arguments[0].value;
                const targetRel = resolveImportPath(source, rel);
                if (!targetRel) return;

                const parent = path.parent;
                // const { A, B } = require(...)
                if (parent.type === "VariableDeclarator" && parent.id.type === "ObjectPattern") {
                    for (const prop of parent.id.properties) {
                        if (prop.type === "ObjectProperty" && prop.value.type === "Identifier") {
                            localMap[prop.value.name] = { targetRel, originalName: prop.key.name };
                        }
                    }
                }

                // require(...).X — handled via MemberExpression parentPath
                if (parent.type === "MemberExpression" && parent.property.type === "Identifier") {
                    const decl = path.parentPath.parentPath?.node;
                    if (decl && decl.type === "VariableDeclarator" && decl.id.type === "Identifier") {
                        localMap[decl.id.name] = { targetRel, originalName: parent.property.name };
                    }
                }

                // const Core = require(...)
                if (parent.type === "VariableDeclarator" && parent.id.type === "Identifier") {
                    localMap[parent.id.name] = { targetRel, originalName: parent.id.name };
                }
            }
        }
    });

    importMap[rel] = localMap;
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
   USAGE DETECTION (Pass 4)
============================== */
const classUsages = {}; // nodeKey -> Set<targetNodeKey>
const functionUsages = {}; // nodeKey -> Set<targetNodeKey>

function detectUsageAndCalls(ast, rel) {
    if (!ast) return;

    const localImports = importMap[rel] || {};
    const nodeStack = [];

    function _isFuncInit(init) {
        return init && (init.type === "FunctionExpression" || init.type === "ArrowFunctionExpression");
    }

    function _recordCall(currentNode, callee) {
        // direct call: fn() or new X()
        if (callee.type === "Identifier") {
            const resolved = _resolveUsageName(callee.name, rel, localImports);
            if (resolved) {
                if (!functionUsages[currentNode]) functionUsages[currentNode] = new Set();
                functionUsages[currentNode].add(resolved);
            }
        }

        // namespace call: Ns.fn() or new Ns.X()
        if (callee.type === "MemberExpression" && callee.object.type === "Identifier") {
            const entry = localImports[callee.object.name];
            if (entry) {
                const targetKey = `${entry.targetRel}:${callee.property.name}`;
                if (nodes.has(targetKey)) {
                    if (!functionUsages[currentNode]) functionUsages[currentNode] = new Set();
                    functionUsages[currentNode].add(targetKey);
                }
            }
        }
    }

    traverse(ast, {
        FunctionDeclaration: {
            enter(path) {
                const name = path.node.id?.name;
                if (name) nodeStack.push(`${rel}:${name}`);
            },
            exit() { nodeStack.pop(); },
        },
        VariableDeclarator: {
            enter(path) {
                const name = path.node.id?.name;
                if (name && _isFuncInit(path.node.init)) {
                    nodeStack.push(`${rel}:${name}`);
                }
            },
            exit(path) {
                const name = path.node.id?.name;
                if (name && _isFuncInit(path.node.init)) {
                    nodeStack.pop();
                }
            },
        },
        ClassDeclaration: {
            enter(path) {
                _handleClassUsage(path, rel, localImports);
                const name = path.node.id?.name;
                nodeStack.push(name ? `${rel}:${name}` : null);
            },
            exit() { nodeStack.pop(); },
        },
        ClassExpression: {
            enter(path) {
              const name = getClassName(path.node, path);
              _handleClassUsage(path, rel, localImports);
              if (name) nodeStack.push(`${rel}:${name}`);
            },
            exit() { nodeStack.pop(); },
        },
        CallExpression(path) {
            if (nodeStack.length === 0 || nodeStack[nodeStack.length - 1] === null) return;
            _recordCall(nodeStack[nodeStack.length - 1], path.node.callee);
        },
        NewExpression(path) {
            if (nodeStack.length === 0 || nodeStack[nodeStack.length - 1] === null) return;
            _recordCall(nodeStack[nodeStack.length - 1], path.node.callee);
        },
    });
}

function _handleClassUsage(path, rel, localImports) {
    const className = getClassName(path.node, path);
    if (!className) return;

    const nodeKey = `${rel}:${className}`;
    const used = new Set();

    path.traverse({
        NewExpression(innerPath) {
            const callee = innerPath.node.callee;
            // new X()
            if (
                callee.type === "Identifier" &&
                callee.name[0] === callee.name[0].toUpperCase() &&
                callee.name[0] !== callee.name[0].toLowerCase()
            ) {
                const resolved = _resolveUsageName(callee.name, rel, localImports);
                if (resolved) used.add(resolved);
            }
            // new Core.X() — namespace constructor
            if (callee.type === "MemberExpression" && callee.object.type === "Identifier") {
                const nsName = callee.object.name;
                const memberName = callee.property.name;
                const entry = localImports[nsName];
                if (entry) {
                    const targetKey = `${entry.targetRel}:${memberName}`;
                    if (nodes.has(targetKey)) used.add(targetKey);
                }
            }
        },
        MemberExpression(innerPath) {
            const obj = innerPath.node.object;
            const prop = innerPath.node.property;
            // X.method() or X.prop — where X is an Identifier with uppercase
            if (obj.type === "Identifier" && prop && prop.type === "Identifier") {
                if (obj.name[0] === obj.name[0].toUpperCase() && obj.name[0] !== obj.name[0].toLowerCase()) {
                    const resolved = _resolveUsageName(obj.name, rel, localImports);
                    if (resolved) used.add(resolved);
                }
            }
            // Core.X.method() — nested MemberExpression
            if (
                obj.type === "MemberExpression" &&
                obj.object.type === "Identifier" &&
                obj.property.type === "Identifier"
            ) {
                const nsName = obj.object.name;
                const memberName = obj.property.name;
                const entry = localImports[nsName];
                if (entry) {
                    const targetKey = `${entry.targetRel}:${memberName}`;
                    if (nodes.has(targetKey)) used.add(targetKey);
                }
            }
        },
    });

    if (used.size > 0) {
        classUsages[nodeKey] = used;
    }
}

function _resolveUsageName(name, sourceRel, localImports) {
    const entry = localImports[name];
    if (entry) {
        const targetKey = `${entry.targetRel}:${entry.originalName}`;
        if (nodes.has(targetKey)) return targetKey;
    }

    const sameFileKey = `${sourceRel}:${name}`;
    if (nodes.has(sameFileKey)) return sameFileKey;

    return null;
}

/* ==============================
   MAIN
============================== */
const files = collectFiles(ROOT_PATH);

// Build AST cache — parse each file once
const astCache = {}; // rel -> ast
for (const file of files) {
    const rel = path.relative(ROOT_PATH, file).split(path.sep).join("/");
    const ast = parseFile(file);
    if (ast) astCache[rel] = ast;
}

// Pass 1+2: declarations and inheritance
for (const [rel, ast] of Object.entries(astCache)) {
  analyzeFile(ast, rel);
}

// Pass 3: collect imports
for (const [rel, ast] of Object.entries(astCache)) {
    collectImports(ast, rel);
}

// Pass 4+4b: detect type usage and function calls (single traversal)
for (const [rel, ast] of Object.entries(astCache)) {
    detectUsageAndCalls(ast, rel);
}

// Pass 5: resolve usage edges
const existingEdges = new Set(edges.map(e => `${e.source}→${e.target}`));

for (const [sourceKey, targets] of Object.entries(classUsages)) {
    for (const targetKey of targets) {
        if (sourceKey === targetKey) continue;
        const pair = `${sourceKey}→${targetKey}`;
        if (!existingEdges.has(pair)) {
            edges.push({ source: sourceKey, target: targetKey });
            existingEdges.add(pair);
        }
    }
}

// Merge function usage edges
for (const [sourceKey, targets] of Object.entries(functionUsages)) {
    for (const targetKey of targets) {
        if (sourceKey === targetKey) continue;
        const pair = `${sourceKey}→${targetKey}`;
        if (!existingEdges.has(pair)) {
            edges.push({ source: sourceKey, target: targetKey });
            existingEdges.add(pair);
        }
    }
}

const output = {
  nodes: Array.from(nodes),
  edges: edges
};

console.log(JSON.stringify(output, null, 2));
"""

import json
import os
import subprocess
import sys
import tempfile


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
        if "@babel" in result.stderr:
            result.stderr = (
                result.stderr + "\nTry to install:\n  * npm install @babel/parser\n  * npm install @babel/traverse"
            )
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)
