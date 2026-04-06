from __future__ import annotations

import os
import typing as t

from tree_sitter import Parser

from . import constants
from .tools import walk_kotlin_files

_OWNER_TYPES: t.Final = frozenset(
    {
        "class_declaration",
        "object_declaration",
    }
)

_BASE_TYPES: t.Final = frozenset(
    {
        "String",
        "Int",
        "Long",
        "Float",
        "Double",
        "Boolean",
        "Byte",
        "Short",
        "Char",
        "Unit",
        "Any",
        "Nothing",
        "Array",
        "List",
        "Map",
        "Set",
        "MutableList",
        "MutableMap",
        "MutableSet",
        "Pair",
        "Triple",
        "Result",
        "Throwable",
        "Exception",
    }
)


def _find_owner(node: t.Any) -> str | None:
    """Walk up the tree to find the enclosing type declaration name."""
    parts: list[str] = []
    current = node.parent

    while current:
        if current.type in _OWNER_TYPES:
            name = None

            for child in current.children:
                if child.type == "identifier":
                    name = child.text.decode()
                    break

            if name:
                parts.append(name)

        current = current.parent

    if not parts:
        return None

    parts.reverse()

    return ".".join(parts)


def _extract_type_usage(filepath: str, rel: str) -> dict[str, set[str]]:
    """Extract type usage pairs from a Kotlin file."""
    with open(filepath, "rb") as f:
        source = f.read()

    parser = Parser(constants.KOTLIN)
    tree = parser.parse(source)

    usage: dict[str, set[str]] = {}

    def _walk(node: t.Any) -> None:
        # user_type > identifier: type references in declarations
        if (
            node.type == "user_type"
            and node.parent
            and node.parent.type
            not in (
                "delegation_specifier",
                "constructor_invocation",
                "explicit_delegation",
            )
        ):
            for child in node.children:
                if child.type == "identifier":
                    type_name = child.text.decode()
                    owner = _find_owner(node)

                    if owner and type_name not in _BASE_TYPES:
                        node_id = f"{rel}:{owner}"
                        usage.setdefault(node_id, set()).add(type_name)

        # call_expression > identifier: constructor calls (filter by uppercase)
        if node.type == "call_expression":
            for child in node.children:
                if child.type == "identifier":
                    type_name = child.text.decode()

                    if type_name and type_name[0].isupper() and type_name not in _BASE_TYPES:
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
    """Resolve used type names to graph node IDs and build usage edges."""
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


def _extract_declarations(filepath: str) -> list[tuple[str, list[str]]]:
    """Extract class, interface, and object declarations from a Kotlin file.

    Recursively scans nested types inside ``class_body`` nodes, producing
    dot-separated names (e.g. ``Outer.Inner``).

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
    _scan_declarations(root, decls, prefix="")

    return decls


def _scan_declarations(
    node: t.Any,
    decls: list[tuple[str, list[str]]],
    prefix: str,
) -> None:
    """Recursively scan AST for type declarations.

    Walks ``class_body`` children to find nested declarations. Skips
    ``function_body`` to avoid scanning lambda bodies.

    Args:
        node: Current tree-sitter AST node.
        decls: Accumulator for (name, supers) tuples.
        prefix: Dot-separated parent class prefix (empty for top-level).
    """
    for child in node.children:
        if child.type == "function_body":
            continue

        if child.type in ("class_declaration", "object_declaration"):
            name_node = child.child_by_field_name("name")

            if name_node:
                name = f"{prefix}{name_node.text.decode()}" if prefix else name_node.text.decode()
                supers = _extract_supers(child)
                decls.append((name, supers))

                # Recurse into class_body for nested declarations
                _scan_declarations(child, decls, prefix=f"{name}.")
        elif child.type in ("class_body", "enum_class_body"):
            _scan_declarations(child, decls, prefix=prefix)


def _resolve_super(
    sup: str,
    source_name: str,
    source_rel: str,
    name_to_files: dict[str, list[str]],
    node_set: set[str],
) -> str | None:
    """Resolve a super type reference to a concrete node ID.

    Tries resolution in order of specificity:
      1. Qualified from enclosing scope (``Container.A`` if source is
         ``Container.B``)
      2. Same as source but without qualification (``A`` as top-level)
      3. Same-file match for the simple name
      4. Any file match for the simple name

    Args:
        sup: Super type name from delegation specifiers (e.g. ``A``).
        source_name: Fully qualified source name (e.g. ``Container.B``).
        source_rel: Relative file path of the source declaration.
        name_to_files: Map of declared name → list of relative file paths.
        node_set: Set of all valid node IDs for filtering.

    Returns:
        A valid node ID string, or None if not resolvable.
    """
    # 1. Try qualified: walk up the enclosing scopes
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

    # 2. Simple name lookup
    files = name_to_files.get(sup)

    if files:
        target_file = source_rel if source_rel in files else files[0]
        target_id = f"{target_file}:{sup}"

        if target_id in node_set:
            return target_id

    return None


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
      - ``explicit_delegation > user_type`` → ``Interface`` (from ``by``)

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

        if child.type == "explicit_delegation":
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


def _is_interface(node: t.Any) -> bool:
    """Check if a class_declaration node is actually an interface.

    Kotlin interfaces are parsed as ``class_declaration`` with an unnamed
    ``interface`` token child by tree-sitter.

    Args:
        node: A tree-sitter class_declaration AST node.

    Returns:
        True if the node represents a Kotlin interface.
    """
    return any(not child.is_named and child.type == "interface" for child in node.children)


def _collect_method_signatures(node: t.Any) -> set[str]:
    """Collect method signatures from a type declaration body.

    A signature is ``name(param_types)`` — simplified for structural
    matching (no return type, matching Go's approach).

    Args:
        node: A tree-sitter class_declaration or object_declaration node.

    Returns:
        Set of method signature strings.
    """
    body = None
    for child in node.children:
        if child.type in ("class_body", "enum_class_body"):
            body = child
            break

    if not body:
        return set()

    sigs: set[str] = set()

    for child in body.children:
        if child.type == "function_declaration":
            name_node = child.child_by_field_name("name")
            if not name_node:
                continue

            name = name_node.text.decode()
            params = _extract_param_types(child)
            sigs.add(f"{name}({','.join(params)})")

    return sigs


def _extract_param_types(func_node: t.Any) -> list[str]:
    """Extract parameter type names from a function_declaration.

    Args:
        func_node: A tree-sitter function_declaration AST node.

    Returns:
        List of simplified type name strings.
    """
    params_node = func_node.child_by_field_name("parameters")
    if not params_node:
        return []

    types: list[str] = []

    for child in params_node.children:
        if child.type != "parameter":
            continue

        for param_child in child.children:
            if param_child.type in ("parameter_with_default",):
                # parameter_with_default > parameter > type
                for pc in param_child.children:
                    if pc.type == "parameter":
                        type_name = _get_simple_type(pc)

                        if type_name:
                            types.append(type_name)
                break

            if param_child.type == "type":
                type_name = _get_simple_type_text(param_child)

                if type_name:
                    types.append(type_name)
                break

    return types


def _get_simple_type(param_node: t.Any) -> str | None:
    """Get simplified type name from a parameter node.

    Args:
        param_node: A tree-sitter parameter AST node.

    Returns:
        Simplified type name, or None.
    """
    for child in param_node.children:
        if child.type == "type":
            return _get_simple_type_text(child)

    return None


def _get_simple_type_text(type_node: t.Any) -> str:
    """Extract a simplified type name from a type node.

    Strips generics and nullable markers for comparison purposes.

    Args:
        type_node: A tree-sitter type AST node.

    Returns:
        Simplified type name string.
    """
    for child in type_node.children:
        if child.type == "user_type":
            ident = _get_identifier(child)
            if ident:
                return ident

        if child.type == "nullable_type":
            for nc in child.children:
                if nc.type == "user_type":
                    ident = _get_identifier(nc)

                    if ident:
                        return ident

        if child.type in ("identifier", "simple_identifier"):
            return child.text.decode()

    return type_node.text.decode()


def _collect_signatures(
    node: t.Any,
    rel: str,
    interface_sigs: dict[str, set[str]],
    class_sigs: dict[str, set[str]],
    prefix: str,
) -> None:
    """Recursively collect method signatures from type declarations.

    Args:
        node: Current tree-sitter AST node.
        rel: Relative file path.
        interface_sigs: Accumulator for interface node_id → signatures.
        class_sigs: Accumulator for class node_id → signatures.
        prefix: Dot-separated parent class prefix.
    """
    for child in node.children:
        if child.type == "function_body":
            continue

        if child.type in ("class_declaration", "object_declaration"):
            name_node = child.child_by_field_name("name")
            if not name_node:
                continue

            name = f"{prefix}{name_node.text.decode()}" if prefix else name_node.text.decode()
            node_id = f"{rel}:{name}"

            sigs = _collect_method_signatures(child)

            if sigs:
                target = interface_sigs if _is_interface(child) else class_sigs
                target[node_id] = sigs

            _collect_signatures(child, rel, interface_sigs, class_sigs, prefix=f"{name}.")
        elif child.type in ("class_body", "enum_class_body"):
            _collect_signatures(child, rel, interface_sigs, class_sigs, prefix=prefix)


def _check_interface_implementation(
    _nodes: list[str],
    edges: list[dict[str, str]],
    _all_decls: list[tuple[str, str, list[str]]],
    path: str,
) -> list[dict[str, str]]:
    """Add implicit interface implementation edges via method signature matching.

    Similar to Go's ``checkInterfaceImplementation``, this collects method
    signatures from interfaces and classes, then adds edges where a class
    implements all methods of an interface but has no explicit edge to it.

    Args:
        _nodes: List of ``file:Name`` node identifiers (reserved for future use).
        edges: Existing edge list (explicit inheritance).
        _all_decls: All declarations as (rel, name, supers) tuples (reserved for future use).
        path: Root project directory.

    Returns:
        Updated edges list with implicit implementation edges added.
    """
    parser = Parser(constants.KOTLIN)

    # Collect method signatures per node
    interface_sigs: dict[str, set[str]] = {}
    class_sigs: dict[str, set[str]] = {}

    for filepath in walk_kotlin_files(path):
        rel = os.path.relpath(filepath, path)

        with open(filepath, "rb") as f:
            source = f.read()

        tree = parser.parse(source)
        _collect_signatures(tree.root_node, rel, interface_sigs, class_sigs, prefix="")

    # Build existing edge set for dedup
    existing = {(e["source"], e["target"]) for e in edges}
    new_edges: list[dict[str, str]] = []

    for class_id, class_methods in class_sigs.items():
        for iface_id, iface_methods in interface_sigs.items():
            if not iface_methods:
                continue

            # Check if class implements all interface methods
            if iface_methods.issubset(class_methods):
                pair = (class_id, iface_id)

                if pair not in existing and class_id != iface_id:
                    new_edges.append({"source": class_id, "target": iface_id})
                    existing.add(pair)

    return edges + new_edges


def analyze(path: str) -> dict[str, t.Any]:
    """Analyze Kotlin source files and build an inheritance graph.

    Uses a two-pass algorithm: first collects all declarations to build a
    complete name-to-files map, then resolves edges with full knowledge.

    Args:
        path: Root directory to scan for Kotlin files.

    Returns:
        Dictionary with ``nodes`` (list of ``file:Name`` strings) and
        ``edges`` (list of ``{source, target}`` dicts).
    """
    # Pass 1: collect all declarations and build name → files map
    all_decls: list[tuple[str, str, list[str]]] = []
    name_to_files: dict[str, list[str]] = {}

    for filepath in walk_kotlin_files(path):
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

    # Add implicit interface implementation edges
    edges = _check_interface_implementation(nodes, edges, all_decls, path)

    # Pass 4: extract type usage
    name_to_node: dict[str, str] = {}
    for node_id in node_set:
        _, name = node_id.rsplit(":", 1)
        name_to_node[name] = node_id

    type_usage: dict[str, set[str]] = {}

    for filepath in walk_kotlin_files(path):
        rel = os.path.relpath(filepath, path)
        for nid, types in _extract_type_usage(filepath, rel).items():
            type_usage.setdefault(nid, set()).update(types)

    # Pass 5: resolve usage edges
    existing = {(e["source"], e["target"]) for e in edges}
    edges.extend(_resolve_usage_edges(type_usage, name_to_node, existing))

    return {"nodes": nodes, "edges": edges}
