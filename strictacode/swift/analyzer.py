from __future__ import annotations

import os
import typing as t

from tree_sitter import Parser

from . import constants
from .tools import walk_swift_files

_DECL_TYPES: t.Final = ("class_declaration", "protocol_declaration")
_BODY_TYPES: t.Final = ("class_body", "protocol_body")

_OWNER_TYPES: t.Final = frozenset(
    {
        "class_declaration",
        "struct_declaration",
        "enum_declaration",
        "actor_declaration",
        "protocol_declaration",
    }
)

_BASE_TYPES: t.Final = frozenset(
    {
        "String",
        "Int",
        "Float",
        "Double",
        "Bool",
        "Void",
        "Any",
        "NSObject",
        "Array",
        "Dictionary",
        "Set",
        "Optional",
        "Result",
        "URL",
        "Data",
        "Date",
        "Error",
        "UUID",
        "Character",
        "Substring",
    }
)


def _resolve_super(
    sup: str,
    source_name: str,
    source_rel: str,
    name_to_files: dict[str, list[str]],
    node_set: set[str],
) -> str | None:
    """Resolve a super type reference to a concrete node ID.

    Args:
        sup: Super type name from inheritance specifiers.
        source_name: Fully qualified source name (e.g. ``Outer.Inner``).
        source_rel: Relative file path of the source declaration.
        name_to_files: Map of declared name → list of relative file paths.
        node_set: Set of all valid node IDs for filtering.

    Returns:
        A valid node ID string, or None if not resolvable.
    """
    # Try qualified from enclosing scope
    parts = source_name.split(".")

    for i in range(len(parts) - 1, 0, -1):
        scope = ".".join(parts[:i])
        qualified = f"{scope}.{sup}"
        files = name_to_files.get(qualified)

        if files:
            target_file = source_rel if source_rel in files else files[0]
            target_id = f"{target_file}:{qualified}"

            if target_id in node_set:
                return target_id

    # Simple name lookup
    files = name_to_files.get(sup)

    if files:
        target_file = source_rel if source_rel in files else files[0]
        target_id = f"{target_file}:{sup}"

        if target_id in node_set:
            return target_id

    return None


def _extract_declarations(filepath: str) -> list[tuple[str, list[str]]]:
    """Extract class and protocol declarations from a Swift file.

    Recursively scans nested types inside ``class_body`` nodes.

    Args:
        filepath: Absolute path to the Swift source file.

    Returns:
        List of ``(name, [super_names])`` tuples.
    """
    with open(filepath, "rb") as f:
        source = f.read()

    parser = Parser(constants.SWIFT)
    tree = parser.parse(source)

    decls: list[tuple[str, list[str]]] = []
    _scan_declarations(tree.root_node, decls, prefix="")

    return decls


def _scan_declarations(
    node: t.Any,
    decls: list[tuple[str, list[str]]],
    prefix: str,
) -> None:
    """Recursively scan AST for type declarations.

    Args:
        node: Current tree-sitter AST node.
        decls: Accumulator for (name, supers) tuples.
        prefix: Dot-separated parent class prefix.
    """
    for child in node.children:
        if child.type in _DECL_TYPES:
            name = _get_decl_name(child)

            if name:
                full = f"{prefix}{name}" if prefix else name
                supers = _extract_supers(child)
                decls.append((full, supers))
                _scan_declarations(child, decls, prefix=f"{full}.")
        elif child.type in _BODY_TYPES:
            _scan_declarations(child, decls, prefix=prefix)


def _get_decl_name(node: t.Any) -> str | None:
    """Get the name of a type declaration node.

    Tries the ``name`` field first, then falls back to ``type_identifier``
    child (Swift tree-sitter stores names as type_identifier in some cases).

    Args:
        node: A tree-sitter class_declaration or protocol_declaration node.

    Returns:
        The type name string, or None.
    """
    name_node = node.child_by_field_name("name")

    if name_node:
        return name_node.text.decode()

    # Fallback: first type_identifier child
    for child in node.children:
        if child.type == "type_identifier":
            return child.text.decode()

    return None


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
            for sub in child.children:
                if sub.type == "user_type":
                    for inner in sub.children:
                        if inner.type == "type_identifier":
                            supers.append(inner.text.decode())
                            break
                    break

    return supers


def _collect_method_signatures(node: t.Any) -> set[str]:
    """Collect method signatures from a type declaration body.

    A signature is ``name(param_types)`` for structural matching.

    Args:
        node: A tree-sitter class_declaration or protocol_declaration node.

    Returns:
        Set of method signature strings.
    """
    body = None
    for child in node.children:
        if child.type in _BODY_TYPES:
            body = child
            break

    if not body:
        return set()

    sigs: set[str] = set()
    func_type = "protocol_function_declaration" if node.type == "protocol_declaration" else "function_declaration"

    for child in body.children:
        if child.type == func_type:
            name = child.child_by_field_name("name")
            if not name:
                # Fallback: simple_identifier child
                for c in child.children:
                    if c.type == "simple_identifier":
                        name = c
                        break

            if not name:
                continue

            params = _extract_param_types(child)
            sigs.add(f"{name.text.decode()}({','.join(params)})")

    return sigs


def _extract_param_types(func_node: t.Any) -> list[str]:
    """Extract parameter type names from a function declaration.

    Args:
        func_node: A tree-sitter function_declaration or protocol_function_declaration node.

    Returns:
        List of simplified type name strings.
    """
    types: list[str] = []

    for child in func_node.children:
        if child.type == "parameter":
            for pc in child.children:
                if pc.type == "type":
                    types.append(_simplify_type(pc))
                    break

    return types


def _simplify_type(type_node: t.Any) -> str:
    """Extract a simplified type name, stripping optionals and generics.

    Args:
        type_node: A tree-sitter type AST node.

    Returns:
        Simplified type name string.
    """
    for child in type_node.children:
        if child.type == "user_type":
            for inner in child.children:
                if inner.type == "type_identifier":
                    return inner.text.decode()

        if child.type == "type_identifier":
            return child.text.decode()

        if child.type == "optional_type":
            for inner in child.children:
                if inner.type == "user_type":
                    for i2 in inner.children:
                        if i2.type == "type_identifier":
                            return i2.text.decode()

    return type_node.text.decode()


def _is_protocol(node: t.Any) -> bool:
    """Check if a node is a protocol declaration.

    Args:
        node: A tree-sitter AST node.

    Returns:
        True if the node is a protocol_declaration.
    """
    return node.type == "protocol_declaration"


def _collect_signatures(
    node: t.Any,
    rel: str,
    protocol_sigs: dict[str, set[str]],
    class_sigs: dict[str, set[str]],
    prefix: str,
) -> None:
    """Recursively collect method signatures from type declarations.

    Args:
        node: Current tree-sitter AST node.
        rel: Relative file path.
        protocol_sigs: Accumulator for protocol signatures.
        class_sigs: Accumulator for class signatures.
        prefix: Dot-separated parent class prefix.
    """
    for child in node.children:
        if child.type in _DECL_TYPES:
            name = _get_decl_name(child)
            if not name:
                continue

            full = f"{prefix}{name}" if prefix else name
            node_id = f"{rel}:{full}"

            sigs = _collect_method_signatures(child)

            if sigs:
                target = protocol_sigs if _is_protocol(child) else class_sigs
                target[node_id] = sigs

            _collect_signatures(child, rel, protocol_sigs, class_sigs, prefix=f"{full}.")
        elif child.type in _BODY_TYPES:
            _collect_signatures(child, rel, protocol_sigs, class_sigs, prefix=prefix)


def _check_protocol_conformance(
    _nodes: list[str],
    edges: list[dict[str, str]],
    _all_decls: list[tuple[str, str, list[str]]],
    path: str,
) -> list[dict[str, str]]:
    """Add implicit protocol conformance edges via method signature matching.

    Similar to Kotlin's interface matching and Go's checkInterfaceImplementation.

    Args:
        _nodes: List of node identifiers (reserved for future use).
        edges: Existing edge list.
        _all_decls: All declarations (reserved for future use).
        path: Root project directory.

    Returns:
        Updated edges list with implicit conformance edges added.
    """
    parser = Parser(constants.SWIFT)

    protocol_sigs: dict[str, set[str]] = {}
    class_sigs: dict[str, set[str]] = {}

    for filepath in walk_swift_files(path):
        rel = os.path.relpath(filepath, path)
        with open(filepath, "rb") as f:
            source = f.read()

        tree = parser.parse(source)
        _collect_signatures(tree.root_node, rel, protocol_sigs, class_sigs, prefix="")

    existing = {(e["source"], e["target"]) for e in edges}

    for class_id, class_methods in class_sigs.items():
        for proto_id, proto_methods in protocol_sigs.items():
            if not proto_methods:
                continue

            if proto_methods.issubset(class_methods):
                pair = (class_id, proto_id)
                if pair not in existing and class_id != proto_id:
                    edges.append({"source": class_id, "target": proto_id})
                    existing.add(pair)

    return edges


def _find_owner(node: t.Any) -> str | None:
    """Walk up the tree to find the enclosing type declaration name.

    Args:
        node: A tree-sitter AST node.

    Returns:
        The fully-qualified owner name (e.g. ``Outer.Inner``), or None.
    """
    parts: list[str] = []
    current = node.parent

    while current:
        if current.type in _OWNER_TYPES:
            name = _get_decl_name(current)
            if name:
                parts.append(name)
        current = current.parent

    if not parts:
        return None

    parts.reverse()
    return ".".join(parts)


def _extract_type_usage(filepath: str, rel: str) -> dict[str, set[str]]:
    """Extract type usage pairs from a Swift file.

    Scans for ``type_annotation`` and ``constructor_expression`` nodes,
    collects referenced type names, and maps them to the enclosing
    type declaration (class/struct/enum/actor).

    Args:
        filepath: Absolute path to the Swift source file.
        rel: Relative file path for node ID construction.

    Returns:
        Mapping of ``rel:OwnerName`` → set of used type name strings.
    """
    with open(filepath, "rb") as f:
        source = f.read()

    parser = Parser(constants.SWIFT)
    tree = parser.parse(source)

    usage: dict[str, set[str]] = {}

    def _collect_type_ids(node: t.Any, out: list[str]) -> None:
        """Recursively collect type_identifier names from a subtree."""
        if node.type == "type_identifier":
            out.append(node.text.decode())
            return
        for child in node.children:
            _collect_type_ids(child, out)

    def _add_usage(node: t.Any) -> None:
        """Extract type identifiers from a node and record usage."""
        owner = _find_owner(node)
        if not owner:
            return
        ids: list[str] = []
        _collect_type_ids(node, ids)
        for type_name in ids:
            if type_name not in _BASE_TYPES:
                node_id = f"{rel}:{owner}"
                usage.setdefault(node_id, set()).add(type_name)

    def _walk(node: t.Any) -> None:
        # type_annotation: var x: Request
        if node.type == "type_annotation":
            _add_usage(node)

        # parameter: _ r: Request  →  user_type child
        if node.type == "parameter":
            _add_usage(node)

        # Return type in function_declaration: func fetch() -> Response
        if node.type == "function_declaration":
            for child in node.children:
                if child.type == "user_type":
                    _add_usage(child)

        # Constructor call: Response() → call_expression with simple_identifier
        if node.type == "call_expression":
            for child in node.children:
                if child.type == "simple_identifier":
                    type_name = child.text.decode()
                    if type_name[0].isupper() and type_name not in _BASE_TYPES:
                        owner = _find_owner(node)
                        if owner:
                            node_id = f"{rel}:{owner}"
                            usage.setdefault(node_id, set()).add(type_name)

        for child in node.children:
            _walk(child)

    _walk(tree.root_node)
    return usage


def _resolve_usage_edges(
    type_usage: dict[str, set[str]],
    name_to_node: dict[str, str],
    existing_edges: set[tuple[str, str]],
) -> list[dict[str, str]]:
    """Resolve used type names to graph node IDs and build usage edges.

    Args:
        type_usage: Mapping of source node ID → set of used type names.
        name_to_node: Mapping of type name → node ID (from declarations).
        existing_edges: Set of (source, target) pairs already in the graph.

    Returns:
        List of new edge dicts with ``source`` and ``target`` keys.
    """
    edges: list[dict[str, str]] = []

    for source_node, used_types in type_usage.items():
        for type_name in used_types:
            target_node = name_to_node.get(type_name)
            if not target_node or target_node == source_node:
                continue

            pair = (source_node, target_node)
            if pair not in existing_edges:
                edges.append({"source": source_node, "target": target_node})
                existing_edges.add(pair)

    return edges


def analyze(path: str) -> dict[str, t.Any]:
    """Analyze Swift source files and build an inheritance graph.

    Uses a two-pass algorithm: first collects all declarations to build a
    complete name-to-files map, then resolves edges with full knowledge.

    Args:
        path: Root directory to scan for Swift files.

    Returns:
        Dictionary with ``nodes`` (list of ``file:Name`` strings) and
        ``edges`` (list of ``{source, target}`` dicts).
    """
    # Pass 1: collect all declarations and build name → files map
    all_decls: list[tuple[str, str, list[str]]] = []
    name_to_files: dict[str, list[str]] = {}

    for filepath in walk_swift_files(path):
        rel = os.path.relpath(filepath, path)
        decls = _extract_declarations(filepath)

        for name, supers in decls:
            all_decls.append((rel, name, supers))
            name_to_files.setdefault(name, [])
            name_to_files[name].append(rel)

    # Build nodes
    nodes: list[str] = []
    for rel, name, _ in all_decls:
        nodes.append(f"{rel}:{name}")

    # Pass 2: resolve edges using complete name knowledge
    node_set = set(nodes)
    edges: list[dict[str, str]] = []

    for rel, name, supers in all_decls:
        node_id = f"{rel}:{name}"

        for sup in supers:
            target_id = _resolve_super(sup, name, rel, name_to_files, node_set)

            if target_id and target_id != node_id:
                edges.append({"source": node_id, "target": target_id})

    # Add implicit protocol conformance edges
    edges = _check_protocol_conformance(nodes, edges, all_decls, path)

    # Pass 4: extract type usage from annotations and constructors
    name_to_node: dict[str, str] = {}
    for node_id in node_set:
        _, name = node_id.rsplit(":", 1)
        name_to_node[name] = node_id

    type_usage: dict[str, set[str]] = {}
    for filepath in walk_swift_files(path):
        rel = os.path.relpath(filepath, path)
        file_usage = _extract_type_usage(filepath, rel)
        for node_id, types in file_usage.items():
            type_usage.setdefault(node_id, set()).update(types)

    # Pass 5: resolve usage edges
    existing = {(e["source"], e["target"]) for e in edges}
    usage_edges = _resolve_usage_edges(type_usage, name_to_node, existing)
    edges.extend(usage_edges)

    return {"nodes": nodes, "edges": edges}
