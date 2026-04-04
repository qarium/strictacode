from __future__ import annotations

import os
import typing as t

from tree_sitter import Parser

from . import constants
from .tools import walk_swift_files


def _parse_file(filepath: str) -> list[dict[str, t.Any]]:
    """Parse a single Swift file and extract type, function, and closure metrics.

    Args:
        filepath: Absolute path to the Swift source file.

    Returns:
        List of metric dictionaries for classes, functions, and closures.
    """
    with open(filepath, "rb") as f:
        source = f.read()

    parser = Parser(constants.SWIFT)
    tree = parser.parse(source)
    root = tree.root_node

    items: list[dict[str, t.Any]] = []
    type_ranges: list[tuple[int, int]] = []  # (start_byte, end_byte) ranges of type bodies

    for child in root.children:
        if child.type == "class_declaration":
            item = _parse_type_declaration(child)

            if item:
                items.append(item)
                type_ranges.append((child.start_byte, child.end_byte))

        elif child.type == "protocol_declaration":
            item = _parse_protocol_declaration(child)

            if item:
                items.append(item)
                type_ranges.append((child.start_byte, child.end_byte))

        elif child.type == "function_declaration":
            # Top-level function
            name_node = child.child_by_field_name("name")

            if not name_node:
                continue

            name = name_node.text.decode()
            lineno = child.start_point[0] + 1
            endline = child.end_point[0] + 1
            body_node = child.child_by_field_name("body")

            if body_node:
                closures = _extract_closures(body_node)
                closure_ranges = [(c["_start_byte"], c["_end_byte"]) for c in closures]
                complexity = _mccabe(body_node, closure_ranges)
            else:
                closures = []
                complexity = 1

            items.append(
                {
                    "type": "function",
                    "name": name,
                    "lineno": lineno,
                    "endline": endline,
                    "complexity": complexity,
                    "methods": [],
                    "closures": [{k: v for k, v in c.items() if not k.startswith("_")} for c in closures],
                }
            )

    return items


def _parse_type_declaration(node: t.Any) -> dict[str, t.Any] | None:
    """Parse class_declaration node (covers struct, class, enum, actor, extension).

    Args:
        node: tree-sitter ``class_declaration`` AST node.

    Returns:
        Metric dictionary or None if the name field is missing.
    """
    name_node = node.child_by_field_name("name")

    if not name_node:
        return None

    name = name_node.text.decode()
    lineno = node.start_point[0] + 1
    endline = node.end_point[0] + 1

    # Find body node (class_body or enum_class_body)
    body_node: t.Any = None

    for child in node.children:
        if child.type in ("class_body", "enum_class_body"):
            body_node = child
            break

    methods: list[dict[str, t.Any]] = []
    class_complexity = 0

    if body_node:
        for child in body_node.children:
            if child.type == "function_declaration":
                method = _parse_method(child, name)

                if method:
                    methods.append(method)
                    class_complexity += method["complexity"]

    return {
        "type": "class",
        "name": name,
        "lineno": lineno,
        "endline": endline,
        "complexity": class_complexity,
        "methods": methods,
        "closures": [],
    }


def _parse_protocol_declaration(node: t.Any) -> dict[str, t.Any] | None:
    """Parse protocol_declaration node.

    Args:
        node: tree-sitter ``protocol_declaration`` AST node.

    Returns:
        Metric dictionary with zero complexity, or None if name is missing.
    """
    name_node = node.child_by_field_name("name")

    if not name_node:
        return None

    name = name_node.text.decode()
    lineno = node.start_point[0] + 1
    endline = node.end_point[0] + 1

    return {
        "type": "class",
        "name": name,
        "lineno": lineno,
        "endline": endline,
        "complexity": 0,
        "methods": [],
        "closures": [],
    }


def _parse_method(node: t.Any, classname: str) -> dict[str, t.Any] | None:
    """Parse a function_declaration inside a type body.

    Args:
        node: tree-sitter ``function_declaration`` AST node.
        classname: Name of the enclosing type.

    Returns:
        Metric dictionary or None if the name field is missing.
    """
    name_node = node.child_by_field_name("name")

    if not name_node:
        return None

    name = name_node.text.decode()
    lineno = node.start_point[0] + 1
    endline = node.end_point[0] + 1

    body_node = node.child_by_field_name("body")

    if body_node:
        closures = _extract_closures(body_node)
        closure_ranges = [(c["_start_byte"], c["_end_byte"]) for c in closures]
        complexity = _mccabe(body_node, closure_ranges)
    else:
        closures = []
        complexity = 1

    return {
        "type": "method",
        "name": name,
        "lineno": lineno,
        "endline": endline,
        "complexity": complexity,
        "classname": classname,
        "methods": [],
        "closures": [{k: v for k, v in c.items() if not k.startswith("_")} for c in closures],
    }


def _extract_closures(body_node: t.Any) -> list[dict[str, t.Any]]:
    """Find lambda_literal (closures) in a function body.

    Args:
        body_node: tree-sitter body AST node to search within.

    Returns:
        List of closure metric dictionaries.
    """
    closures: list[dict[str, t.Any]] = []

    for child in body_node.children:
        _find_closures_recursive(child, closures)

    return closures


def _find_closures_recursive(node: t.Any, closures: list[dict[str, t.Any]]) -> None:
    """Recursively find lambda_literal nodes, skipping nested function declarations.

    Args:
        node: tree-sitter AST node to traverse.
        closures: Accumulator list for found closures.
    """
    if node.type == "function_declaration":
        return  # Don't descend into nested functions

    if node.type == "lambda_literal":
        name = _find_closure_name(node)
        lineno = node.start_point[0] + 1
        endline = node.end_point[0] + 1

        # Count complexity within the lambda
        nested_closures: list[dict[str, t.Any]] = []

        for child in node.children:
            _find_closures_recursive(child, nested_closures)

        closure_ranges = [(c["_start_byte"], c["_end_byte"]) for c in nested_closures]
        complexity = _mccabe(node, closure_ranges)

        closures.append(
            {
                "type": "function",
                "name": name,
                "lineno": lineno,
                "endline": endline,
                "complexity": complexity,
                "closures": [{k: v for k, v in c.items() if not k.startswith("_")} for c in nested_closures],
                "_start_byte": node.start_byte,
                "_end_byte": node.end_byte,
            }
        )
        return

    for child in node.children:
        _find_closures_recursive(child, closures)


def _find_closure_name(lambda_node: t.Any) -> str:
    """Find the name of a closure by looking at parent property_declaration.

    Args:
        lambda_node: tree-sitter ``lambda_literal`` AST node.

    Returns:
        Variable name from the property declaration, or ``"<closure>"``.
    """
    parent = lambda_node.parent

    if parent and parent.type == "property_declaration":
        for child in parent.children:
            if child.type == "pattern":
                for sub in child.children:
                    if sub.type == "simple_identifier":
                        return sub.text.decode()

    return "<closure>"


def _mccabe(node: t.Any, skip_ranges: list[tuple[int, int]] | None = None) -> int:
    """Calculate McCabe complexity by counting decision points in the AST.

    Args:
        node: tree-sitter AST node to analyze.
        skip_ranges: Byte ranges to exclude from counting (e.g., nested closures).

    Returns:
        McCabe complexity score (minimum 1).
    """
    if skip_ranges is None:
        skip_ranges = []

    complexity_ref = [1]
    _count_decisions(node, skip_ranges, complexity_ref)

    return complexity_ref[0]


# Use a mutable list to allow recursive accumulation
def _count_decisions(node: t.Any, skip_ranges: list[tuple[int, int]], complexity_ref: list[int]) -> None:
    """Recursively count decision points in the AST, skipping specified byte ranges.

    Args:
        node: tree-sitter AST node to traverse.
        skip_ranges: Byte ranges to exclude from counting (e.g., closures).
        complexity_ref: Mutable list with a single integer for accumulation.
    """
    # Skip nodes entirely within a skip range (e.g., closures)
    for start, end in skip_ranges:
        if node.start_byte >= start and node.end_byte <= end:
            return

    decision_types = constants.DECISION_NODES | {
        "switch_entry",
        "catch_block",
        constants.CONJUNCTION,
        constants.DISJUNCTION,
    }

    if node.type in decision_types:
        complexity_ref[0] += 1

    for child in node.children:
        _count_decisions(child, skip_ranges, complexity_ref)


def collect(path: str) -> dict[str, list[dict[str, t.Any]]]:
    """Collect metrics from Swift source files in the given directory tree.

    Args:
        path: Root directory to scan for Swift files.

    Returns:
        Mapping of relative file paths to lists of metric dictionaries.
    """
    result: dict[str, list[dict[str, t.Any]]] = {}

    for filepath in walk_swift_files(path):
        rel = os.path.relpath(filepath, path)
        items = _parse_file(filepath)

        if items:
            result[rel] = items

    return result
