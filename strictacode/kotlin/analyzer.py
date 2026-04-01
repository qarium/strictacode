r"""
import java.io.File

// ==============================
// CONFIG
// ==============================
val IGNORED_DIRS = setOf("build", ".gradle", ".idea", ".git")
val IGNORED_FILE_SUFFIXES = listOf("Test.kt", "Spec.kt")

val ROOT_PATH = if (args.isNotEmpty()) args[0] else "."

// ==============================
// FILE WALKER (same as collector)
// ==============================
fun shouldIgnoreFile(file: File): Boolean {
    val name = file.name
    return IGNORED_FILE_SUFFIXES.any { name.endsWith(it) }
}

fun shouldIgnoreDir(dir: File): Boolean {
    return dir.name in IGNORED_DIRS
}

fun collectKtFiles(root: File): List<File> {
    val result = mutableListOf<File>()
    fun walk(dir: File) {
        dir.listFiles()?.forEach { f ->
            when {
                f.isDirectory && !shouldIgnoreDir(f) -> walk(f)
                f.isFile && f.extension == "kt" && !shouldIgnoreFile(f) -> result.add(f)
            }
        }
    }
    walk(root)
    return result
}

// ==============================
// EXTRACT INHERITANCE RELATIONS
// ==============================
data class TypeDecl(val name: String, val supers: List<String>, val file: String, val line: Int)

val CLASS_DECL = Regex(
    "^\\s*(?:public\\s+|private\\s+|protected\\s+|internal\\s+)?+" +
    "(?:data\\s+|sealed\\s+|open\\s+|abstract\\s+|inner\\s+|enum\\s+)*" +
    "class\\s+(\\w+)" +
    "(?:\\s*<[^>]*>)?" +  // type params
    "(?:\\s*\\([^)]*\\))?" +  // constructor params
    "\\s*(?::\\s*(.+))?$"
)
val OBJECT_DECL = Regex(
    "^\\s*(?:public\\s+|private\\s+|protected\\s+|internal\\s+)?+" +
    "object\\s+(\\w+)" +
    "\\s*(?::\\s*(.+))?$"
)
val INTERFACE_DECL = Regex(
    "^\\s*(?:public\\s+|private\\s+|protected\\s+|internal\\s+)?+" +
    "interface\\s+(\\w+)" +
    "(?:\\s*<[^>]*>)?" +
    "\\s*(?::\\s*(.+))?$"
)
val ENUM_CLASS_DECL = Regex(
    "^\\s*(?:public\\s+|private\\s+|protected\\s+|internal\\s+)?+" +
    "enum\\s+class\\s+(\\w+)" +
    "(?:\\s*\\([^)]*\\))?" +
    "\\s*(?::\\s*(.+))?$"
)

fun parseSupers(supersStr: String): List<String> {
    // Parse: "Base(), Interface1, Interface2" or "Base"
    val result = mutableListOf<String>()
    var depth = 0
    var current = StringBuilder()
    for (ch in supersStr) {
        when (ch) {
            '(' -> depth++
            ')' -> depth--
            ',' -> {
                if (depth == 0) {
                    val name = current.toString().trim()
                    if (name.isNotEmpty()) result.add(name)
                    current = StringBuilder()
                } else {
                    current.append(ch)
                }
            }
            else -> current.append(ch)
        }
    }
    val last = current.toString().trim()
    if (last.isNotEmpty()) result.add(last)
    // Strip () from names: "Base()" -> "Base"
    return result.map { it.replace(Regex("\\(.*\\)"), "").trim() }.filter { it.isNotEmpty() }
}

fun analyzeFile(file: File, rootPath: String): List<TypeDecl> {
    val lines = file.readLines()
    val rel = file.relativeTo(File(rootPath)).path
    val decls = mutableListOf<TypeDecl>()

    for ((idx, line) in lines.withIndex()) {
        val trimmed = line.trim()
        if (trimmed.startsWith("//") || trimmed.startsWith("/*") || trimmed.startsWith("*")) continue

        // Try enum class first (most specific)
        val enumMatch = ENUM_CLASS_DECL.find(line)
        if (enumMatch != null) {
            val name = enumMatch.groupValues[1]
            val supers = enumMatch.groupValues[2]?.let { parseSupers(it) } ?: emptyList()
            decls.add(TypeDecl(name, supers, rel, idx + 1))
            continue
        }

        // Try interface
        val ifaceMatch = INTERFACE_DECL.find(line)
        if (ifaceMatch != null) {
            val name = ifaceMatch.groupValues[1]
            val supers = ifaceMatch.groupValues[2]?.let { parseSupers(it) } ?: emptyList()
            decls.add(TypeDecl(name, supers, rel, idx + 1))
            continue
        }

        // Try object
        val objMatch = OBJECT_DECL.find(line)
        if (objMatch != null) {
            val name = objMatch.groupValues[1]
            val supers = objMatch.groupValues[2]?.let { parseSupers(it) } ?: emptyList()
            decls.add(TypeDecl(name, supers, rel, idx + 1))
            continue
        }

        // Try class (least specific, after enum)
        val classMatch = CLASS_DECL.find(line)
        if (classMatch != null) {
            val name = classMatch.groupValues[1]
            val supers = classMatch.groupValues[2]?.let { parseSupers(it) } ?: emptyList()
            decls.add(TypeDecl(name, supers, rel, idx + 1))
        }
    }

    return decls
}

// ==============================
// JSON SERIALIZATION (manual, no external deps)
// ==============================
fun escapeJson(s: String): String {
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\t", "\\t")
}

fun toJsonValue(v: Any?): String = when (v) {
    null -> "null"
    is String -> "\"${escapeJson(v)}\""
    is Number -> v.toString()
    is Boolean -> v.toString()
    is Map<*, *> -> {
        val entries = v.entries.map { (k, vv) -> "\"${escapeJson(k.toString())}\":${toJsonValue(vv)}" }
        "{${entries.joinToString(",")}}"
    }
    is List<*> -> {
        val items = v.map { toJsonValue(it) }
        "[${items.joinToString(",")}]"
    }
    else -> "\"${escapeJson(v.toString())}\""
}

// ==============================
// MAIN
// ==============================
val root = File(ROOT_PATH).absoluteFile
val files = collectKtFiles(root)
val allDecls = mutableListOf<TypeDecl>()

for (file in files) {
    allDecls.addAll(analyzeFile(file, root.path))
}

// Build nodes and edges
val nodes = mutableListOf<String>()
val edges = mutableListOf<Map<String, String>>()
val nameToFile = mutableMapOf<String, String>()

for (decl in allDecls) {
    val nodeId = "${decl.file}:${decl.name}"
    nodes.add(nodeId)
    nameToFile[decl.name] = decl.file
}

for (decl in allDecls) {
    val sourceId = "${decl.file}:${decl.name}"
    for (sup in decl.supers) {
        // Find the super type's file
        val superFile = nameToFile[sup] ?: continue  // skip unknown types
        val targetId = "$superFile:$sup"
        edges.add(mapOf("source" to sourceId, "target" to targetId))
    }
}

val output = mapOf("nodes" to nodes, "edges" to edges)
println(toJsonValue(output))
"""

import json
import os
import subprocess
import tempfile


def analyze(path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        kts_file = os.path.join(tmpdir, "analyzer.kts")
        with open(kts_file, "w") as f:
            f.write(__doc__)

        cmd = ["kotlinc", "-script", kts_file, path]
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        if "kotlinc" in result.stderr.lower() or "not found" in result.stderr.lower():
            raise RuntimeError(
                "kotlinc not found. Install Kotlin SDK: https://kotlinlang.org/docs/command-line.html"
            )
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)
