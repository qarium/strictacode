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
function safeLoc(node, type) {
  if (!node.loc) return 0;
  return type === "start" ? node.loc.start.line : node.loc.end.line;
}
function getFunctionName(node, parent) {
  if (node.id?.name) return node.id.name;
  if (!parent) return null;
  if (parent.type === "VariableDeclarator" && parent.id.name) return parent.id.name;
  if (parent.type === "AssignmentExpression" && parent.left.name) return parent.left.name;
  if (parent.type === "ObjectProperty" && parent.key.name) return parent.key.name;
  return null;
}
function getVariableName(path) {
  const parent = path.parent;
  if (parent.type === "VariableDeclarator") return parent.id.name;
  if (parent.type === "AssignmentExpression" && parent.left.name) return parent.left.name;
  return null;
}

/* ==============================
   COMPLEXITY
============================== */
function calculateComplexity(node) {
  let complexity = 1;
  traverse(node, {
    noScope: true,
    enter(path) {
      switch (path.node.type) {
        case "IfStatement":
        case "ForStatement":
        case "ForInStatement":
        case "ForOfStatement":
        case "WhileStatement":
        case "DoWhileStatement":
        case "CatchClause":
        case "ConditionalExpression":
          complexity++;
          break;
        case "LogicalExpression":
          if (path.node.operator === "&&" || path.node.operator === "||") complexity++;
          break;
        case "SwitchCase":
          if (path.node.test) complexity++;
          break;
      }
    }
  });
  return complexity;
}

/* ==============================
   FUNCTION / CLOSURE HANDLER
============================== */
const functionStack = [];

function createFunctionNode(node, parent, typeOverride = "function") {
  const name = getFunctionName(node, parent);
  if (!name) return null;

  const fn = {
    type: typeOverride,
    lineno: safeLoc(node, "start"),
    complexity: calculateComplexity(node),
    endline: safeLoc(node, "end"),
    name,
    closures: []
  };

  if (functionStack.length) {
    functionStack[functionStack.length - 1].closures.push(fn);
  }

  return fn;
}

/* ==============================
   CLASS HANDLER
============================== */
function handleClass(node, path, results) {
  const className = node.id?.name ?? getVariableName(path);
  if (!className) return;

  const classObj = {
    type: "class",
    lineno: safeLoc(node, "start"),
    complexity: 0, // будем суммировать методы
    endline: safeLoc(node, "end"),
    name: className,
    methods: []
  };

  results.push(classObj);

  path.traverse({
    ClassMethod(methodPath) { handleMethod(methodPath, classObj); },
    ClassPrivateMethod(methodPath) { handleMethod(methodPath, classObj); }
  });
}

function handleMethod(methodPath, classObj) {
  const node = methodPath.node;
  const name = node.key?.name ?? node.key?.value;
  if (!name) return null;

  const methodObj = {
    type: "method",
    lineno: safeLoc(node, "start"),
    complexity: calculateComplexity(node),
    endline: safeLoc(node, "end"),
    name,
    classname: classObj.name,
    closures: []
  };

  classObj.methods.push(methodObj);
  classObj.complexity += methodObj.complexity;

  functionStack.push(methodObj);
  methodPath.traverse({
    FunctionDeclaration(innerPath) {
      const fn = createFunctionNode(innerPath.node, innerPath.parent);
      if (fn) {
        functionStack.push(fn);
        innerPath.skip();
        functionStack.pop();
      }
    },
    FunctionExpression(innerPath) {
      const fn = createFunctionNode(innerPath.node, innerPath.parent);
      if (fn) {
        functionStack.push(fn);
        innerPath.skip();
        functionStack.pop();
      }
    },
    ArrowFunctionExpression(innerPath) {
      const fn = createFunctionNode(innerPath.node, innerPath.parent);
      if (fn) {
        functionStack.push(fn);
        innerPath.skip();
        functionStack.pop();
      }
    }
  });
  functionStack.pop();

  return methodObj;
}

/* ==============================
   ANALYZE FILE
============================== */
function analyzeFile(filePath) {
  const code = fs.readFileSync(filePath, "utf8");
  let ast;
  try {
    ast = parser.parse(code, {
      sourceType: "unambiguous",
      plugins: [
        "typescript","jsx",
        "classProperties","dynamicImport",
        "optionalChaining","nullishCoalescingOperator"
      ]
    });
  } catch {
    return [];
  }

  const results = [];

  traverse(ast, {
    ClassDeclaration(path) { handleClass(path.node, path, results); },
    ClassExpression(path) { handleClass(path.node, path, results); },

    FunctionDeclaration: {
      enter(path) {
        const fn = createFunctionNode(path.node, path.parent);
        if (!fn) return;
        functionStack.push(fn);
        if (!functionStack[0]?.closures.includes(fn)) results.push(fn);
      },
      exit() { if (functionStack.length) functionStack.pop(); }
    },
    FunctionExpression: {
      enter(path) {
        const fn = createFunctionNode(path.node, path.parent);
        if (!fn) return;
        functionStack.push(fn);
        if (!functionStack[0]?.closures.includes(fn)) results.push(fn);
      },
      exit() { if (functionStack.length) functionStack.pop(); }
    },
    ArrowFunctionExpression: {
      enter(path) {
        const fn = createFunctionNode(path.node, path.parent);
        if (!fn) return;
        functionStack.push(fn);
        if (!functionStack[0]?.closures.includes(fn)) results.push(fn);
      },
      exit() { if (functionStack.length) functionStack.pop(); }
    }
  });

  return results;
}

/* ==============================
   MAIN
============================== */
const files = collectFiles(ROOT_PATH);
const output = {};

for (const file of files) {
  const rel = path.relative(ROOT_PATH, file);
  const analyzed = analyzeFile(file);
  if (analyzed.length > 0) output[rel] = analyzed;
}

console.log(JSON.stringify(output, null, 2));
"""

import os
import sys
import json
import tempfile
import subprocess


def collect(path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        js_file = os.path.join(tmpdir, "metrics.js")
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
