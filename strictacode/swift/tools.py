from __future__ import annotations

import os
import typing as t

from strictacode.swift import constants


def walk_swift_files(root: str) -> t.Iterator[str]:
    """Yield paths to Swift source files, skipping ignored directories and test files."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in constants.IGNORED_DIRS]

        for fname in sorted(filenames):
            if fname.endswith(".swift") and not any(fname.endswith(s) for s in constants.IGNORED_SUFFIXES):
                yield os.path.join(dirpath, fname)
