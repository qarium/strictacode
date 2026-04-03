from __future__ import annotations

import os
import typing as t

from tree_sitter import Parser

from . import constants
from .tools import walk_kotlin_files


def analyze(path: str) -> dict[str, t.Any]:
    """Analyze Kotlin source files and build an inheritance graph.

    Args:
        path: Root directory to scan for Kotlin files.

    Returns:
        Dictionary with ``nodes`` (list of ``file:Name`` strings) and
        ``edges`` (list of ``{source, target}`` dicts).
    """
    nodes: list[str] = []
    edges: list[dict[str, str]] = []
    name_to_file: dict[str, str] = {}

    for filepath in walk_kotlin_files(path):
        rel = os.path.relpath(filepath, path)
        decls = _extract_declarations(filepath)

        for name, supers in decls:
            node_id = f"{rel}:{name}"
            nodes.append(node_id)
            name_to_file[name] = rel

            for sup in supers:
                target_file = name_to_file.get(sup, "")
                target_id = f"{target_file}:{sup}" if target_file else f":{sup}"
                edges.append({"source": node_id, "target": target_id})

    # Filter edges where target not found in project
    node_set = set(nodes)
    edges = [e for e in edges if e["target"] in node_set]

    return {"nodes": nodes, "edges": edges}


def _extract_declarations(filepath: str) -> list[tuple[str, list[str]]]:
    """Extract class, interface, and object declarations from a Kotlin file.

    Args:
        filepath: Absolute path to the Kotlin source file.

    Returns:
        List of (name, supers) tuples for each declared type.
    """
    with open(filepath, "rb") as f:
        source = f.read()

    parser = Parser(constants.KOTLIN)
    tree = parser.parse(source)
    root = tree.root_node

    decls: list[tuple[str, list[str]]] = []

    for child in root.children:
        if child.type in ("class_declaration", "object_declaration"):
            name_node = child.child_by_field_name("name")

            if name_node:
                name = name_node.text.decode()
                supers = _extract_supers(child)
                decls.append((name, supers))

    return decls


def _extract_supers(node: t.Any) -> list[str]:
    """Extract parent class and interface names from delegation specifiers.

    Handles both simple type references (``Service``) and constructor
    invocations (``Base()``).

    Args:
        node: A tree-sitter class_declaration or object_declaration AST node.

    Returns:
        List of parent type name strings.
    """
    supers: list[str] = []

    for child in node.children:
        if child.type == "delegation_specifiers":
            for spec in child.children:
                if spec.type == "delegation_specifier":
                    name = _extract_type_name(spec)

                    if name:
                        supers.append(name)

    return supers


def _extract_type_name(spec: t.Any) -> str | None:
    """Extract type name from a delegation_specifier node.

    Handles:
      - ``user_type > identifier`` → ``Service``
      - ``constructor_invocation > user_type > identifier`` → ``Base``

    Args:
        spec: A tree-sitter delegation_specifier AST node.

    Returns:
        The type name string, or None if not found.
    """
    for child in spec.children:
        if child.type == "user_type":
            return _get_identifier(child)

        if child.type == "constructor_invocation":
            for inner in child.children:
                if inner.type == "user_type":
                    return _get_identifier(inner)

    return None


def _get_identifier(user_type_node: t.Any) -> str | None:
    """Get the identifier text from a user_type node.

    Args:
        user_type_node: A tree-sitter user_type AST node.

    Returns:
        Decoded identifier text, or None.
    """
    for child in user_type_node.children:
        if child.type == "identifier":
            return child.text.decode()

    return None
