r"""
import java.io.File

// ==============================
// CONFIG
// ==============================
val IGNORED_DIRS = setOf("build", ".gradle", ".idea", ".git")
val IGNORED_FILE_SUFFIXES = listOf("Test.kt", "Spec.kt")

val ROOT_PATH = if (args.isNotEmpty()) args[0] else "."

// ==============================
// FILE WALKER
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
// BRACE BALANCING — find block range
// startIdx is 0-based line index where the declaration starts.
// Returns 1-based endline.
// If expression body (= without {), returns startIdx + 1.
// ==============================
fun findBlockRange(lines: List<String>, startIdx: Int): Int {
    val line = lines[startIdx]
    // Check for expression body: fun foo(...) = expr  (no brace on same line)
    if (!line.contains("{")) {
        // Look for = outside of parameter list
        val eqIdx = line.indexOf('=')
        if (eqIdx > 0 && line.substring(eqIdx - 1, eqIdx) != "=" && line.substring(eqIdx + 1).trim().isNotEmpty()) {
            // expression body, single line
            return startIdx + 1
        }
    }

    var depth = 0
    var foundOpen = false
    for (i in startIdx until lines.size) {
        var inString = false
        var stringChar = '"'
        var j = 0
        while (j < lines[i].length) {
            val ch = lines[i][j]
            if (inString) {
                if (ch == '\\') { j++; }  // skip escaped char
                else if (ch == stringChar) { inString = false }
            } else {
                when (ch) {
                    '"' -> { inString = true; stringChar = '"' }
                    '\'' -> { inString = true; stringChar = '\'' }
                    '/' -> {
                        if (j + 1 < lines[i].length) {
                            val next = lines[i][j + 1]
                            if (next == '/') break  // line comment, skip rest
                        }
                    }
                    '{' -> { depth++; foundOpen = true }
                    '}' -> depth--
                }
            }
            j++
        }
        if (foundOpen && depth <= 0) return i + 1
    }
    return lines.size
}

// ==============================
// MCCABE COMPLEXITY
// skipRanges: 0-based line ranges to skip (e.g. closure bodies)
// ==============================
fun mccabeComplexity(
    lines: List<String>,
    startLine: Int,
    endLine: Int,
    skipRanges: List<Pair<Int, Int>> = emptyList()
): Int {
    var complexity = 1
    for (i in (startLine - 1) until endLine) {
        if (i >= lines.size) break
        // Skip lines that belong to nested closures
        if (skipRanges.any { (s, e) -> i >= s && i < e }) continue
        val line = lines[i]
        val trimmed = line.trim()
        if (trimmed.startsWith("//")) continue

        complexity += Regex("\\bif\\b").findAll(line).count()
        complexity += Regex("\\bfor\\b").findAll(line).count()
        complexity += Regex("\\bwhile\\b").findAll(line).count()
        complexity += Regex("\\bcatch\\b").findAll(line).count()
        complexity += Regex("&&").findAll(line).count()
        complexity += Regex("\\|\\|").findAll(line).count()
        // when branches: lines like "value ->" or "else ->"
        // but NOT lambda arrows like "x: Int ->" or "{ x ->"
        if (trimmed.contains("->") && !trimmed.startsWith("when") && !trimmed.startsWith("//")
            && !trimmed.contains("{") && !trimmed.startsWith("val") && !trimmed.startsWith("var")) {
            complexity++
        }
    }
    return complexity
}

// ==============================
// EXTRACT CLOSURES (lambdas)
// ==============================
fun extractClosures(lines: List<String>, parentStart: Int, parentEnd: Int): List<Map<String, Any>> {
    val closures = mutableListOf<Map<String, Any>>()
    // Match: val/var name = { ... or just { params ->
    val lambdaAssignPattern = Regex("(?:val|var)\\s+(\\w+)\\s*(?::\\s*[^=]+)?=\\s*\\{")
    val lambdaArrowPattern = Regex("\\{[^}]*->")
    var i = parentStart - 1
    while (i < parentEnd && i < lines.size) {
        val line = lines[i]
        val trimmed = line.trim()
        if (trimmed.startsWith("//") || trimmed.startsWith("*") || trimmed.startsWith("/*")) {
            i++; continue
        }
        // Skip declarations
        if (trimmed.startsWith("fun ") || trimmed.startsWith("class ") || trimmed.startsWith("object ")
            || trimmed.startsWith("interface ") || trimmed.startsWith("enum ")
            || trimmed.startsWith("data class ")) {
            i++; continue
        }
        val assignMatch = lambdaAssignPattern.find(line)
        if (assignMatch != null) {
            val name = assignMatch.groupValues[1]
            val endline = findBlockRange(lines, i)
            val complexity = mccabeComplexity(lines, i + 1, endline)
            closures.add(mapOf(
                "type" to "function",
                "name" to name,
                "lineno" to i + 1,
                "endline" to endline,
                "complexity" to complexity,
                "closures" to emptyList<Map<String, Any>>()
            ))
            i = endline
            continue
        }
        val arrowMatch = lambdaArrowPattern.find(line)
        if (arrowMatch != null && "{" in line && "->" in line) {
            // Anonymous lambda like: items.map { x -> ... }
            val endline = findBlockRange(lines, i)
            val complexity = mccabeComplexity(lines, i + 1, endline)
            closures.add(mapOf(
                "type" to "function",
                "name" to "closure",
                "lineno" to i + 1,
                "endline" to endline,
                "complexity" to complexity,
                "closures" to emptyList<Map<String, Any>>()
            ))
            i = endline
            continue
        }
        i++
    }
    return closures
}

// ==============================
// PARSERS
// ==============================
val CLASS_PATTERN = Regex(
    "^\\s*(?:public\\s+|private\\s+|protected\\s+|internal\\s+)?+" +
    "(?:data\\s+|sealed\\s+|open\\s+|abstract\\s+|inner\\s+)*" +
    "(?:class|object)\\s+(\\w+)"
)
val INTERFACE_PATTERN = Regex(
    "^\\s*(?:public\\s+|private\\s+|protected\\s+|internal\\s+)?+" +
    "interface\\s+(\\w+)"
)
val ENUM_CLASS_PATTERN = Regex(
    "^\\s*(?:public\\s+|private\\s+|protected\\s+|internal\\s+)?+" +
    "enum\\s+class\\s+(\\w+)"
)
val METHOD_PATTERN = Regex(
    "^\\s+fun\\s+(\\w+)\\s*[<(]"
)
val TOPLEVEL_FUN_PATTERN = Regex(
    "^fun\\s+(\\w+)\\s*[<(]"
)

fun parseFile(file: File, rootPath: String): List<Map<String, Any>> {
    val lines = file.readLines()
    val result = mutableListOf<Map<String, Any>>()
    val processedLines = mutableSetOf<Int>()

    // Pass 1: Find classes, objects, interfaces, enums
    val classRanges = mutableListOf<Triple<String, Int, Int>>()
    for (i in lines.indices) {
        val line = lines[i]
        val enumMatch = ENUM_CLASS_PATTERN.find(line)
        val ifaceMatch = if (enumMatch == null) INTERFACE_PATTERN.find(line) else null
        val classMatch = if (enumMatch == null && ifaceMatch == null) CLASS_PATTERN.find(line) else null

        val match = enumMatch ?: ifaceMatch ?: classMatch ?: continue
        val name = match.groupValues[1]
        if (name in listOf("get", "set", "when", "for", "while", "if", "do")) continue

        val endline = findBlockRange(lines, i)
        classRanges.add(Triple(name, i + 1, endline))

        for (l in i until endline) processedLines.add(l)
    }

    // Build class items with methods
    for ((className, startLine, endLine) in classRanges) {
        val methods = mutableListOf<Map<String, Any>>()
        var classComplexity = 0

        for (i in (startLine - 1) until endLine) {
            if (i >= lines.size) break
            val methodMatch = METHOD_PATTERN.find(lines[i])
            if (methodMatch != null) {
                val methodName = methodMatch.groupValues[1]
                val methodEnd = findBlockRange(lines, i)
                val closures = extractClosures(lines, i + 1, methodEnd)
                val closureRanges = closures.map { (it["lineno"] as Int - 1) to (it["endline"] as Int) }
                val methodComplexity = mccabeComplexity(lines, i + 1, methodEnd, closureRanges)
                classComplexity += methodComplexity

                methods.add(mapOf(
                    "type" to "method",
                    "name" to methodName,
                    "lineno" to i + 1,
                    "endline" to methodEnd,
                    "complexity" to methodComplexity,
                    "classname" to className,
                    "methods" to emptyList<Map<String, Any>>(),
                    "closures" to closures
                ))
            }
        }

        result.add(mapOf(
            "type" to "class",
            "name" to className,
            "lineno" to startLine,
            "endline" to endLine,
            "complexity" to classComplexity,
            "methods" to methods,
            "closures" to emptyList<Map<String, Any>>()
        ))
    }

    // Pass 2: Find top-level functions (only in lines NOT part of a class)
    for (i in lines.indices) {
        if (i in processedLines) continue
        val line = lines[i]
        val funMatch = TOPLEVEL_FUN_PATTERN.find(line) ?: continue
        val funName = funMatch.groupValues[1]
        val endline = findBlockRange(lines, i)
        var hasBody = false
        for (l in i until minOf(endline, lines.size)) {
            if ("{" in lines[l]) { hasBody = true; break }
            if ("=" in lines[l] && "{" !in lines[l]) break
        }
        val closures = if (hasBody) extractClosures(lines, i + 1, endline) else emptyList()
        val closureRanges = closures.map { (it["lineno"] as Int - 1) to (it["endline"] as Int) }
        val complexity = if (hasBody) mccabeComplexity(lines, i + 1, endline, closureRanges) else 1

        result.add(mapOf(
            "type" to "function",
            "name" to funName,
            "lineno" to i + 1,
            "endline" to endline,
            "complexity" to complexity,
            "methods" to emptyList<Map<String, Any>>(),
            "closures" to closures
        ))
        for (l in i until endline) processedLines.add(l)
    }

    return result
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
val output = mutableMapOf<String, List<Map<String, Any>>>()

for (file in files) {
    val rel = file.relativeTo(root).path
    val parsed = parseFile(file, root.path)
    if (parsed.isNotEmpty()) {
        output[rel] = parsed
    }
}

println(toJsonValue(output))
"""

import json
import os
import subprocess
import tempfile


def collect(path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        kts_file = os.path.join(tmpdir, "collector.kts")
        with open(kts_file, "w") as f:
            f.write(__doc__)

        cmd = ["kotlinc", "-script", kts_file, path]
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        if "kotlinc" in result.stderr.lower() or "not found" in result.stderr.lower():
            raise RuntimeError("kotlinc not found. Install Kotlin SDK: https://kotlinlang.org/docs/command-line.html")
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)
