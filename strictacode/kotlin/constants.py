from __future__ import annotations

import typing as t

import tree_sitter_kotlin as tskotlin
from tree_sitter import Language

KOTLIN: t.Final[Language] = Language(tskotlin.language())

IGNORED_DIRS: t.Final[frozenset[str]] = frozenset({"build", ".gradle", ".idea", ".git", "target", "out"})
IGNORED_SUFFIXES: t.Final[tuple[str, ...]] = ("Test.kt", "Spec.kt", "Tests.kt")

# Decision point node types for McCabe complexity
DECISION_NODES: t.Final[frozenset[str]] = frozenset({
    "if_expression",
    "for_statement",
    "while_statement",
    "do_while_statement",
})

# When expression entries — each non-else when_entry adds +1
WHEN_ENTRY: t.Final[str] = "when_entry"

# Binary expression with logical operators adds complexity
BINARY_EXPRESSION: t.Final[str] = "binary_expression"
LOGICAL_OPS: t.Final[frozenset[str]] = frozenset({"&&", "||"})
