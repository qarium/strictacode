from collections import defaultdict

from ..loader import FileItem, FileItemTypes, Loader
from . import collector
from .analyzer import Analyzer


def _build_name_to_node(nodes) -> dict[str, list[str]]:
    """Build a mapping from short class names to full node IDs.

    Args:
        nodes: Set of node IDs in ``filepath:ClassName`` format.

    Returns:
        Dict mapping class name to list of full node IDs, sorted for determinism.
    """
    name_to_nodes: dict[str, list[str]] = {}
    for node_id in nodes:
        if ":" in node_id:
            _, name = node_id.rsplit(":", 1)
            name_to_nodes.setdefault(name, []).append(node_id)
    for name in name_to_nodes:
        name_to_nodes[name].sort()
    return name_to_nodes


def _resolve_edges(graph, name_to_node: dict[str, list[str]], import_maps: dict):
    """Resolve short inheritance edge targets to full node IDs.

    Args:
        graph: The dependency graph to resolve edges in-place.
        name_to_node: Mapping from short names to lists of full node IDs.
        import_maps: Mapping from module path to import_map dicts.
    """
    resolved_edges = {}
    for src, targets in graph.edges.items():
        resolved = set()
        src_path = src.split(":", 1)[0]
        import_map = import_maps.get(src_path, {})
        for tgt in targets:
            if ":" in tgt:
                resolved.add(tgt)
                continue
            imported_name = import_map.get(tgt)
            if imported_name:
                candidates = name_to_node.get(imported_name, [])
                matched = [n for n in candidates if n.endswith(f":{imported_name}")]
                if matched:
                    resolved.update(matched)
                    continue
            candidates = name_to_node.get(tgt, [])
            if candidates:
                resolved.update(candidates)
            else:
                resolved.add(tgt)
        resolved_edges[src] = resolved

    graph.clear_edges()
    for src, targets in resolved_edges.items():
        for tgt in targets:
            graph.add_edge(src, tgt)


def _collect_existing_pairs(graph) -> set[tuple[str, str]]:
    """Collect all existing (src, tgt) edge pairs from graph.

    Args:
        graph: The dependency graph to scan.

    Returns:
        Set of (source, target) tuples for all existing edges.
    """
    pairs = set()
    for src, targets in graph.edges.items():
        for tgt in targets:
            pairs.add((src, tgt))
    return pairs


def _resolve_targets(type_name: str, import_map: dict[str, str], name_to_node: dict[str, list[str]]) -> list[str]:
    """Resolve a type name to full node IDs using import map and global lookup.

    Args:
        type_name: Short type name found in usage.
        import_map: Mapping from local names to imported names.
        name_to_node: Mapping from short names to lists of full node IDs.

    Returns:
        List of full node IDs matching the type name.
    """
    imported_name = import_map.get(type_name)
    if imported_name:
        candidates = name_to_node.get(imported_name, [])
        matched = [n for n in candidates if n.endswith(f":{imported_name}")]
        if matched:
            return matched
    candidates = name_to_node.get(type_name, [])
    if candidates:
        return candidates
    return []


def _create_item(**kwargs) -> FileItem:
    """Create a ``FileItem`` from a raw metric dict.

    Args:
        **kwargs: Raw metric fields from the collector output.

    Returns:
        A populated ``FileItem`` with nested methods and closures.
    """
    return FileItem(
        type=kwargs["type"],
        name=kwargs["name"],
        lineno=kwargs["lineno"],
        endline=kwargs["endline"],
        complexity=kwargs["complexity"],
        class_name=kwargs.get("classname"),
        methods=[_create_item(**i) for i in (kwargs.get("methods") or [])],
        closures=[_create_item(**i) for i in (kwargs.get("closures") or [])],
    )


class PyLoder(Loader):
    __lang__ = "python"
    __ignore_dirs__ = [
        ".venv",
        "venv",
        ".env",
        "env",
    ]
    __comment_line_prefixes__ = ["#"]
    __comment_code_blocks__ = [
        ("'''", "'''"),
        ('"""', '"""'),
    ]

    def collect(self) -> dict[str, list[FileItem]]:
        data = collector.collect(self.root)

        file_to_items = {}

        for filepath, items in data.items():
            if not isinstance(items, list):
                continue

            if filepath not in file_to_items:
                file_to_items[filepath] = []

            file_to_items[filepath].extend(_create_item(**i) for i in items)
            file_to_items[filepath].sort(key=lambda i: 0 if i.type == FileItemTypes.CLASS else 1)

        return file_to_items

    def _collect_analyzer_data(self) -> tuple[dict, dict, dict, dict]:
        """Run Analyzer on all modules and collect classes, bases, imports, and type usage.

        Returns:
            Tuple of (class_methods, class_bases, import_maps, type_usages).
        """
        class_methods = {}
        class_bases = defaultdict(list)
        import_maps = {}
        type_usages = {}

        for module in self.sources.modules:
            analyzer = Analyzer.file(module.path)

            if not analyzer:
                continue

            for cls in analyzer.classes:
                class_methods[cls] = analyzer.classes[cls]

            for cls, bases in analyzer.class_bases.items():
                class_bases[cls].extend(bases)

            import_maps[module.path] = analyzer.import_map
            type_usages[module.path] = analyzer.type_usage

        return class_methods, class_bases, import_maps, type_usages

    def _add_usage_edges(self, type_usages: dict, import_maps: dict, name_to_node: dict[str, list[str]]):
        """Resolve type usage references and add edges for matching classes.

        Args:
            type_usages: Mapping from module path to type_usage dicts.
            import_maps: Mapping from module path to import_map dicts.
            name_to_node: Mapping from short names to lists of full node IDs.
        """
        existing = _collect_existing_pairs(self.sources.graph)

        for module_path, type_usage in type_usages.items():
            import_map = import_maps.get(module_path, {})
            for source_node, used_types in type_usage.items():
                for type_name in used_types:
                    for target in _resolve_targets(type_name, import_map, name_to_node):
                        if target != source_node:
                            pair = (source_node, target)
                            if pair not in existing:
                                self.sources.graph.add_edge(source_node, target)
                                existing.add(pair)

    def build(self):
        """Build the dependency graph from analyzed modules.

        Collects classes, inheritance edges, and type usage edges
        across all modules. Resolves short names to full node IDs.
        """
        class_methods, class_bases, import_maps, type_usages = self._collect_analyzer_data()

        for cls in class_methods:
            self.sources.graph.add_node(cls)

        # Pass 3: inheritance edges
        for cls, bases in class_bases.items():
            for base in bases:
                self.sources.graph.add_edge(cls, base)

        # Resolve short names to full node IDs
        name_to_node = _build_name_to_node(self.sources.graph.nodes)
        _resolve_edges(self.sources.graph, name_to_node, import_maps)

        # Pass 5: resolve usage edges
        self._add_usage_edges(type_usages, import_maps, name_to_node)
