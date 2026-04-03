from __future__ import annotations

import os
import typing as t

from strictacode.kotlin import constants


def walk_kotlin_files(root: str) -> t.Iterator[str]:
    """Yield paths to Kotlin source files, skipping ignored directories and test files."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in constants.IGNORED_DIRS]

        for fname in sorted(filenames):
            if fname.endswith(".kt") and not any(fname.endswith(s) for s in constants.IGNORED_SUFFIXES):
                yield os.path.join(dirpath, fname)
