from __future__ import annotations

import os
import typing as t

from tree_sitter import Parser

from . import constants
from .tools import walk_kotlin_files

# Dispatch table: node type → parser function (populated after all definitions)
_NODE_PARSERS: dict[str, t.Callable[[t.Any], dict[str, t.Any] | None]] = {}


def collect(path: str) -> dict[str, list[dict[str, t.Any]]]:
    """Collect metrics from Kotlin source files in the given directory tree.

    Args:
        path: Root directory to scan for Kotlin files.

    Returns:
        Mapping of relative file paths to lists of metric dictionaries.
    """
    result: dict[str, list[dict[str, t.Any]]] = {}

    for filepath in walk_kotlin_files(path):
        rel = os.path.relpath(filepath, path)
        items = _parse_file(filepath)

        if items:
            result[rel] = items

    return result


def _parse_file(filepath: str) -> list[dict[str, t.Any]]:
    """Parse a single Kotlin file and extract type, function, and closure metrics.

    Args:
        filepath: Absolute path to the Kotlin source file.

    Returns:
        List of metric dictionaries for classes, objects, and top-level functions.
    """
    with open(filepath, "rb") as f:
        source = f.read()

    parser = Parser(constants.KOTLIN)
    tree = parser.parse(source)
    root = tree.root_node

    items: list[dict[str, t.Any]] = []

    for child in root.children:
        parser_fn = _NODE_PARSERS.get(child.type)

        if parser_fn:
            item = parser_fn(child)

            if item:
                items.append(item)

    return items


def _is_interface(node: t.Any) -> bool:
    """Check if a class_declaration node is actually an interface.

    Args:
        node: A tree-sitter class_declaration AST node.

    Returns:
        True if the node has an unnamed ``interface`` token child.
    """
    return any(not child.is_named and child.type == "interface" for child in node.children)


def _get_function_body(node: t.Any) -> t.Any | None:
    """Get the function_body child node from a function_declaration.

    Args:
        node: A tree-sitter function_declaration AST node.

    Returns:
        The block node inside function_body, the function_body itself for
        expression bodies, or None if absent.
    """
    for child in node.children:
        if child.type == "function_body":
            for inner in child.children:
                if inner.type == "block":
                    return inner
            return child
    return None


def _extract_type_body(node: t.Any, body_types: tuple[str, ...] = ("class_body", "enum_class_body")) -> t.Any | None:
    """Find the body node matching one of the given types.

    Args:
        node: A tree-sitter AST node to search children of.
        body_types: Tuple of node type strings to match.

    Returns:
        The first matching child node, or None.
    """
    for child in node.children:
        if child.type in body_types:
            return child
    return None


def _extract_methods(body_node: t.Any, classname: str) -> list[dict[str, t.Any]]:
    """Extract function_declaration methods from a body node.

    Args:
        body_node: A tree-sitter class_body or enum_class_body AST node.
        classname: Name of the enclosing type (used as classname in methods).

    Returns:
        List of method metric dictionaries.
    """
    methods: list[dict[str, t.Any]] = []

    for child in body_node.children:
        if child.type == "function_declaration":
            method = _parse_method(child, classname)

            if method:
                methods.append(method)

    return methods


def _compute_body_metrics(body_node: t.Any | None) -> tuple[list[dict[str, t.Any]], int]:
    """Compute closures and McCabe complexity for a function/method body.

    Args:
        body_node: The AST node for the function body, or None.

    Returns:
        Tuple of (closures list with internal keys, complexity int).
    """
    if not body_node:
        return [], 1

    closures = _extract_closures(body_node)
    closure_ranges = [(c["_start_byte"], c["_end_byte"]) for c in closures]
    complexity = _mccabe(body_node, closure_ranges)

    return closures, complexity


def _clean_closures(closures: list[dict[str, t.Any]]) -> list[dict[str, t.Any]]:
    """Remove internal keys (prefixed with _) from closure dicts.

    Args:
        closures: List of closure dictionaries with internal ``_``-prefixed keys.

    Returns:
        List of closure dictionaries without internal keys.
    """
    return [{k: v for k, v in c.items() if not k.startswith("_")} for c in closures]


def _parse_type_declaration(node: t.Any) -> dict[str, t.Any] | None:
    """Parse class_declaration or object_declaration node.

    Args:
        node: A tree-sitter class_declaration or object_declaration AST node.

    Returns:
        Metric dictionary for the type, or None if name is missing.
    """
    name_node = node.child_by_field_name("name")

    if not name_node:
        return None

    name = name_node.text.decode()

    lineno = node.start_point[0] + 1
    endline = node.end_point[0] + 1

    body_node = _extract_type_body(node, ("class_body",)) if _is_interface(node) else _extract_type_body(node)

    methods = _extract_methods(body_node, name) if body_node else []

    return {
        "type": "class",
        "name": name,
        "lineno": lineno,
        "endline": endline,
        "complexity": sum(m["complexity"] for m in methods),
        "methods": methods,
        "closures": [],
    }


def _parse_toplevel_function(node: t.Any) -> dict[str, t.Any] | None:
    """Parse a top-level function_declaration.

    Args:
        node: A tree-sitter function_declaration AST node.

    Returns:
        Metric dictionary for the function, or None if name is missing.
    """
    name_node = node.child_by_field_name("name")

    if not name_node:
        return None

    name = name_node.text.decode()

    lineno = node.start_point[0] + 1
    endline = node.end_point[0] + 1

    body_node = _get_function_body(node)
    closures, complexity = _compute_body_metrics(body_node)

    return {
        "type": "function",
        "name": name,
        "lineno": lineno,
        "endline": endline,
        "complexity": complexity,
        "methods": [],
        "closures": _clean_closures(closures),
    }


def _parse_method(node: t.Any, classname: str) -> dict[str, t.Any] | None:
    """Parse a function_declaration inside a type body.

    Args:
        node: A tree-sitter function_declaration AST node.
        classname: Name of the enclosing type.

    Returns:
        Metric dictionary for the method, or None if name is missing.
    """
    name_node = node.child_by_field_name("name")

    if not name_node:
        return None

    name = name_node.text.decode()

    lineno = node.start_point[0] + 1
    endline = node.end_point[0] + 1

    body_node = _get_function_body(node)
    closures, complexity = _compute_body_metrics(body_node)

    return {
        "type": "method",
        "name": name,
        "lineno": lineno,
        "endline": endline,
        "complexity": complexity,
        "classname": classname,
        "methods": [],
        "closures": _clean_closures(closures),
    }


def _extract_closures(body_node: t.Any) -> list[dict[str, t.Any]]:
    """Find lambda_literal (closures) in a function body.

    Args:
        body_node: A tree-sitter block or lambda_literal AST node.

    Returns:
        List of closure dictionaries with internal ``_``-prefixed keys.
    """
    closures: list[dict[str, t.Any]] = []

    for child in body_node.children:
        _find_closures_recursive(child, closures)

    return closures


def _find_closures_recursive(node: t.Any, closures: list[dict[str, t.Any]]) -> None:
    """Recursively find lambda_literal nodes, skipping nested function declarations.

    Args:
        node: Current tree-sitter AST node to examine.
        closures: Accumulator list to append found closures to.
    """
    if node.type == "function_declaration":
        return

    if node.type == "lambda_literal":
        name = _find_closure_name(node)

        lineno = node.start_point[0] + 1
        endline = node.end_point[0] + 1

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
                "closures": _clean_closures(nested_closures),
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
        lambda_node: A tree-sitter lambda_literal AST node.

    Returns:
        Variable name the lambda is assigned to, or ``"<closure>"``.
    """
    parent = lambda_node.parent

    if not parent:
        return "<closure>"

    if parent.type == "variable_declaration":
        for child in parent.children:
            if child.type == "identifier":
                return child.text.decode()

    grandparent = parent.parent

    if grandparent and grandparent.type == "property_declaration":
        for child in grandparent.children:
            if child.type == "variable_declaration":
                for vc in child.children:
                    if vc.type == "identifier":
                        return vc.text.decode()

    return "<closure>"


def _mccabe(node: t.Any, skip_ranges: list[tuple[int, int]] | None = None) -> int:
    """Calculate McCabe complexity by counting decision points in the AST.

    Args:
        node: Root tree-sitter AST node to analyze.
        skip_ranges: Optional list of (start_byte, end_byte) ranges to exclude.

    Returns:
        McCabe cyclomatic complexity score (minimum 1).
    """
    if skip_ranges is None:
        skip_ranges = []

    complexity_ref = [1]
    _count_decisions(node, skip_ranges, complexity_ref)

    return complexity_ref[0]


def _count_decisions(node: t.Any, skip_ranges: list[tuple[int, int]], complexity_ref: list[int]) -> None:
    """Recursively count decision points in the AST, skipping specified byte ranges.

    Args:
        node: Current tree-sitter AST node.
        skip_ranges: Byte ranges of nested closures to exclude from counting.
        complexity_ref: Single-element list holding the running complexity total.
    """
    for start, end in skip_ranges:
        if node.start_byte >= start and node.end_byte <= end:
            return

    decision_types = constants.DECISION_NODES | {"catch_block"}

    if node.type in decision_types:
        complexity_ref[0] += 1

    if node.type == constants.BINARY_EXPRESSION and _is_logical_op(node):
        complexity_ref[0] += 1

    if node.type == constants.WHEN_ENTRY:
        if not _is_else_entry(node):
            complexity_ref[0] += 1
        return

    for child in node.children:
        _count_decisions(child, skip_ranges, complexity_ref)


def _is_logical_op(node: t.Any) -> bool:
    """Check if a binary_expression node uses ``&&`` or ``||`` operator.

    Args:
        node: A tree-sitter binary_expression AST node.

    Returns:
        True if the expression uses a logical conjunction or disjunction.
    """
    return any(not child.is_named and child.type in constants.LOGICAL_OPS for child in node.children)


def _is_else_entry(node: t.Any) -> bool:
    """Check if a when_entry node is an else branch.

    Args:
        node: A tree-sitter when_entry AST node.

    Returns:
        True if the entry starts with the ``else`` keyword.
    """
    for child in node.children:
        if not child.is_named and child.type == "else":
            return True
        if child.is_named:
            return False
    return True


# Populate dispatch table
_NODE_PARSERS.update(
    {
        "class_declaration": _parse_type_declaration,
        "object_declaration": _parse_type_declaration,
        "function_declaration": _parse_toplevel_function,
    }
)
