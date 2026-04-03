from __future__ import annotations

import os
import typing as t

from tree_sitter import Parser

from . import constants
from .tools import walk_swift_files


def analyze(path: str) -> dict[str, t.Any]:
    """Analyze Swift source files and build an inheritance graph.

    Args:
        path: Root directory to scan for Swift files.

    Returns:
        Dictionary with ``nodes`` (list of ``file:Name`` strings) and
        ``edges`` (list of ``{source, target}`` dicts).
    """
    nodes: list[str] = []
    edges: list[dict[str, str]] = []
    name_to_file: dict[str, str] = {}

    for filepath in walk_swift_files(path):
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
    """Extract class and protocol declarations from a Swift file.

    Args:
        filepath: Absolute path to the Swift source file.

    Returns:
        List of ``(name, [super_names])`` tuples.
    """
    with open(filepath, "rb") as f:
        source = f.read()

    parser = Parser(constants.SWIFT)
    tree = parser.parse(source)
    root = tree.root_node

    decls: list[tuple[str, list[str]]] = []

    for child in root.children:
        if child.type in ("class_declaration", "protocol_declaration"):
            name_node = child.child_by_field_name("name")

            if name_node:
                name = name_node.text.decode()
                supers = _extract_supers(child)
                decls.append((name, supers))

    return decls


def _extract_supers(node: t.Any) -> list[str]:
    """Extract parent class and protocol names from inheritance specifiers.

    Args:
        node: tree-sitter AST node (class or protocol declaration).

    Returns:
        List of inherited type name strings.
    """
    supers: list[str] = []

    for child in node.children:
        if child.type == "inheritance_specifier":
            # Contains user_type with the name
            for sub in child.children:
                if sub.type == "user_type":
                    for inner in sub.children:
                        if inner.type == "type_identifier":
                            supers.append(inner.text.decode())
                            break
                    break

    return supers
