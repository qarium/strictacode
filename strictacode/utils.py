import fnmatch
import os
import sys
from contextlib import contextmanager
from pathlib import Path


# AGENT: добавь докстринг к функции
def lines_of_code(
    file_path: str,
    *,
    lineno: int | None = None,
    endline: int | None = None,
    ignore_prefixes: list[str] | None = None,
    ignore_blocks: list[tuple[str, str]] | None = None,
) -> int:
    """Count non-blank lines of code in a file.

    Optionally limits the range and skips lines matching
    configurable prefixes or block markers.

    Args:
        file_path: Path to the source file.
        lineno: Starting line number (1-based). Counts from the
            beginning if None.
        endline: Ending line number (1-based). Counts to the end
            if None.
        ignore_prefixes: Line prefixes to skip (e.g. comments).
        ignore_blocks: Tuples of (start_marker, end_marker) defining
            blocks to skip entirely.

    Returns:
        Number of non-blank, non-ignored lines.
    """
    line_count = 0
    line_number = 0
    ignore_blocks = ignore_blocks or []
    ignore_prefixes = ignore_prefixes or []

    def get_stop_pointer(line):
        for block in ignore_blocks:
            if line.startswith(block[0]):
                return block[1]
        return None

    with open(file_path, encoding="utf-8") as file:
        stop_pointer = None

        for line in file:
            line_number += 1

            if lineno and line_number < lineno:
                continue
            if endline and line_number > endline:
                break

            line = line.strip()

            if not line:
                continue

            if stop_pointer is not None and line.startswith(stop_pointer):
                stop_pointer = None
                continue

            if stop_pointer is None:
                stop_pointer = get_stop_pointer(line)

            if stop_pointer is not None:
                continue

            if any(line.startswith(i) for i in ignore_prefixes):
                continue

            line_count += 1

    return line_count


# AGENT: добавь докстринг к функции
def _parse_gitignore(project_path):
    """Parse .gitignore into a list of pattern strings.

    Skips blank lines and comment lines (starting with ``#``).

    Args:
        project_path: Absolute or relative path to the project root.

    Returns:
        List of patterns, or an empty list if .gitignore is missing.
    """
    gitignore_path = os.path.join(project_path, ".gitignore")

    if not os.path.isfile(gitignore_path):
        return []

    patterns = []
    with open(gitignore_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                patterns.append(line)

    return patterns


# AGENT: добавь докстринг к функции
def _should_exclude(name, patterns):
    """Check whether *name* matches any of the given patterns.

    Directory patterns (ending with ``/``) are matched without the
    trailing slash.

    Args:
        name: File or directory name to check.
        patterns: Glob patterns, typically from ``.gitignore``.

    Returns:
        True if *name* matches at least one pattern.
    """
    for pattern in patterns:
        if pattern.endswith("/"):
            pattern = pattern[:-1]

        if fnmatch.fnmatch(name, pattern):
            return True

    return False


# AGENT: добавь докстринг к функции
def ignore_dirs(path, *, exclude_patterns: list[str] | None = None):
    """Recursively collect directories excluded by .gitignore patterns.

    If *exclude_patterns* is None the patterns are read from
    ``.gitignore`` in *path*.

    Args:
        path: Root directory to walk.
        exclude_patterns: Explicit glob patterns. Read from .gitignore
            when None.

    Returns:
        Flat list of excluded directory paths (relative to *path*).
    """
    exclude_patterns = _parse_gitignore(path) if exclude_patterns is None else exclude_patterns

    exclude_dirs = []

    for _, dirs, _ in os.walk(path):
        exclude = [d for d in dirs if _should_exclude(d, exclude_patterns)]
        include = [d for d in dirs if not _should_exclude(d, exclude_patterns)]

        exclude_dirs.extend(exclude)

        for dir_name in include:
            exclude_dirs.extend(ignore_dirs(os.path.join(path, dir_name)))

    return exclude_dirs


# AGENT: добавь докстринг к функции
def source_content(filepath: str, lineno: int, endline: int) -> str:
    """Read a range of lines from a source file.

    Args:
        filepath: Path to the file.
        lineno: Starting line number (1-based, inclusive).
        endline: Ending line number (1-based, inclusive).

    Returns:
        Joined lines within the specified range.
    """
    with open(filepath, encoding="utf-8") as file:
        lines = []
        line_number = 0

        for line in file:
            line_number += 1

            if line_number < lineno:
                continue
            if line_number > endline:
                break

            lines.append(line)

        return "\n".join(lines)


# AGENT: добавь докстринг к функции
def detect_languages(path):
    """Detect all programming languages present in a directory tree.

    Walks the tree respecting .gitignore and identifies languages
    by file extension (``.py``, ``.go``, ``.js``/``.ts``, ``.kt``).

    Args:
        path: Root directory to scan.

    Returns:
        List of language name strings (e.g. ``["python", "kotlin"]``).
    """
    languages = set()
    exclude_patterns = _parse_gitignore(path)

    for _root, dirs, files in os.walk(path):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if not _should_exclude(d, exclude_patterns)]

        for f in files:
            ext = Path(f).suffix.lower()
            if ext == ".py":
                languages.add("python")
            elif ext == ".go":
                languages.add("golang")
            elif ext in (".js", ".ts"):
                languages.add("javascript")
            elif ext == ".kt":
                languages.add("kotlin")

    return list(languages)


# AGENT: добавь докстринг к функции
def detect_language(path):
    """Detect the dominant programming language in a directory tree.

    Counts files by extension (respecting .gitignore) and returns
    the language with the most files.

    Args:
        path: Root directory to scan.

    Returns:
        Language name string, or None if no recognised files found.
    """
    exclude_patterns = _parse_gitignore(path)

    lang_counts = {}

    for _root, dirs, files in os.walk(path):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if not _should_exclude(d, exclude_patterns)]

        for f in files:
            ext = Path(f).suffix.lower()
            if ext == ".py":
                lang_counts["python"] = lang_counts.get("python", 0) + 1
            elif ext == ".go":
                lang_counts["golang"] = lang_counts.get("golang", 0) + 1
            elif ext in (".js", ".ts"):
                lang_counts["javascript"] = lang_counts.get("javascript", 0) + 1
            elif ext == ".kt":
                lang_counts["kotlin"] = lang_counts.get("kotlin", 0) + 1

    if not lang_counts:
        return None

    return max(lang_counts.items(), key=lambda x: x[1])[0]


@contextmanager
def redirect_output(output: str):
    """Redirect stdout and stderr to a file.

    Opens the file at ``output`` for writing and replaces
    ``sys.stdout`` and ``sys.stderr`` with the file object.
    Restores the original streams after exiting the context.

    Args:
        output: Path to the file where stdout and stderr will be written.
    """
    stderr = sys.stderr
    stdout = sys.stdout

    with open(output, "w") as fo:
        sys.stderr = fo
        sys.stdout = fo

        try:
            yield
        finally:
            sys.stderr = stderr
            sys.stdout = stdout
