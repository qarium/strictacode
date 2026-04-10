import radon.complexity as cc_mod
from radon.cli.tools import cc_to_dict, iter_filenames
from radon.complexity import cc_visit, sorted_results


def collect(path: str) -> dict:
    """Run radon cyclomatic complexity analysis on a Python project.

    Uses radon library API directly instead of CLI subprocess to avoid
    configparser issues with setup.cfg files containing ``%()`` syntax.

    Args:
        path: Root directory or file path to analyze.

    Returns:
        Mapping from filepath to list of block dicts with keys:
        type, name, lineno, endline, complexity, rank, col_offset,
        and optionally classname, methods, closures.
    """
    result = {}

    for filepath in iter_filenames([path]):
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        try:
            blocks = cc_visit(source)
        except SyntaxError:
            continue

        sorted_blocks = sorted_results(blocks, order=cc_mod.SCORE)
        dicts = [cc_to_dict(b) for b in sorted_blocks]

        if dicts:
            result[filepath] = dicts

    return result
