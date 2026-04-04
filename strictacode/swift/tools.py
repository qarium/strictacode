from __future__ import annotations

import os
import typing as t

from strictacode.swift import constants


def walk_swift_files(root: str) -> t.Iterator[str]:
    """Yield paths to Swift source files, skipping ignored directories and test files."""
    for dirpath, dirnames, filenames in os.walk(root):
        _filter_dirs(dirnames)

        for fname in sorted(filenames):
            if _is_swift_source(fname):
                yield os.path.join(dirpath, fname)


def _filter_dirs(dirnames: list[str]) -> None:
    """Remove ignored directories from the walk list in-place.

    Args:
        dirnames: Mutable list of directory names to filter.
    """
    dirnames[:] = [d for d in dirnames if d not in constants.IGNORED_DIRS]


def _is_swift_source(filename: str) -> bool:
    """Check if a filename is a non-test Swift source file.

    Args:
        filename: Basename of the file to check.

    Returns:
        True if the file has a ``.swift`` extension and is not a test file.
    """
    return filename.endswith(".swift") and not any(filename.endswith(s) for s in constants.IGNORED_SUFFIXES)
