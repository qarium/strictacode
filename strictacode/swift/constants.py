from __future__ import annotations

import typing as t

import tree_sitter_swift as tsswift
from tree_sitter import Language

SWIFT: t.Final[Language] = Language(tsswift.language())

IGNORED_DIRS: t.Final[frozenset[str]] = frozenset({".build", ".swiftpm", "DerivedData", "Packages", ".git", "build"})
IGNORED_SUFFIXES: t.Final[tuple[str, ...]] = ("Test.swift", "Spec.swift", "Tests.swift")

# Decision point node types for McCabe complexity
DECISION_NODES: t.Final[frozenset[str]] = frozenset({
    "if_statement",
    "guard_statement",
    "for_statement",
    "while_statement",
    "repeat_while_statement",
})

# Binary expression types that add complexity
CONJUNCTION: t.Final[str] = "conjunction_expression"  # &&
DISJUNCTION: t.Final[str] = "disjunction_expression"  # ||
