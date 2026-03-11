import os
import fnmatch
import typing as t
from pathlib import Path


def lines_of_code(file_path: str, *,
                  lineno: t.Optional[int] = None,
                  endline: t.Optional[int] = None,
                  ignore_prefixes: t.Optional[list[str]] = None,
                  ignore_blocks: t.Optional[list[tuple[str, str]]] = None) -> int:
    line_count = 0
    line_number = 0
    ignore_blocks = ignore_blocks or []
    ignore_prefixes = ignore_prefixes or []

    def get_stop_pointer(l):
        for block in ignore_blocks:
            if l.startswith(block[0]):
                return block[1]
        return None

    with open(file_path, 'r', encoding='utf-8') as file:
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

            stop_pointer = get_stop_pointer(line)

            if stop_pointer is not None:
                continue

            if any(line.startswith(i) for i in ignore_prefixes):
                continue

            line_count += 1

    return line_count


def _parse_gitignore(project_path):
    gitignore_path = os.path.join(project_path, ".gitignore")

    if not os.path.isfile(gitignore_path):
        return []

    patterns = []
    with open(gitignore_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                patterns.append(line)

    return patterns


def _should_exclude(name, patterns):
    for pattern in patterns:
        if pattern.endswith("/"):
            pattern = pattern[:-1]

        if fnmatch.fnmatch(name, pattern):
            return True

    return False


def ignore_dirs(path, *, exclude_patterns: t.Optional[list[str]] = None):
    exclude_patterns = _parse_gitignore(path) if exclude_patterns is None else exclude_patterns

    exclude_dirs = []

    for _, dirs, _ in os.walk(path):
        exclude = [d for d in dirs if _should_exclude(d, exclude_patterns)]
        include = [d for d in dirs if not _should_exclude(d, exclude_patterns)]

        exclude_dirs.extend(exclude)

        for dir_name in include:
            exclude_dirs.extend(ignore_dirs(os.path.join(path, dir_name)))

    return exclude_dirs


def source_content(filepath: str, lineno: int, endline: int) -> str:
    with open(filepath, 'r', encoding='utf-8') as file:
        lines = []
        line_number = 0

        for line in file:
            line_number += 1

            if line_number < lineno:
                continue
            if line_number > endline:
                break

            lines.append(line)

        return '\n'.join(lines)


def detect_languages(path):
    languages = set()
    exclude_patterns = _parse_gitignore(path)

    for root, dirs, files in os.walk(path):
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

    return list(languages)


def detect_language(path):
    exclude_patterns = _parse_gitignore(path)

    lang_counts = {}

    for root, dirs, files in os.walk(path):
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

    if not lang_counts:
        return None

    return max(lang_counts.items(), key=lambda x: x[1])[0]
