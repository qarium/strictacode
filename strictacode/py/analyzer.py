import ast
import typing as t
from collections import defaultdict
from pathlib import Path


class Analyzer(ast.NodeVisitor):
    def __init__(self, filepath: str, module: str):
        """Initialize analyzer for a specific source file.

        Args:
            filepath: Absolute path to the Python source file.
            module: Dotted module path derived from the file location.
        """
        self.filepath = filepath
        self.module = module

        self.classes = {}
        self.class_bases = defaultdict(list)
        self.import_map: dict[str, str] = {}
        self.type_usage: dict[str, set[str]] = {}

        self.current_class = None

    @classmethod
    def file(cls, filepath: str) -> t.Optional["Analyzer"]:
        """Parse a Python file and run the analyzer on its AST.

        Args:
            filepath: Absolute path to the Python source file.

        Returns:
            An ``Analyzer`` instance with collected data, or ``None`` on syntax error.
        """
        path = Path(filepath)
        module = path.with_suffix("")
        module = ".".join(module.parts)

        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            return None

        analyzer = cls(filepath, module)
        analyzer.visit(tree)

        return analyzer

    def visit_ClassDef(self, node):
        """Register a class and collect its base class names."""
        cname = f"{self.filepath}:{node.name}"

        self.classes[cname] = {"methods": 0}
        self.current_class = cname

        for base in node.bases:
            if isinstance(base, ast.Name):
                self.class_bases[cname].append(base.id)

            if isinstance(base, ast.Attribute):
                self.class_bases[cname].append(base.attr)

        for kw in node.keywords:
            if kw.arg == "metaclass" and isinstance(kw.value, ast.Name):
                self.class_bases[cname].append(kw.value.id)

        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        """Count methods inside classes."""
        if self.current_class:
            self.classes[self.current_class]["methods"] += 1
        self.generic_visit(node)

    def visit_Call(self, node):
        """Record constructor calls with uppercase names as type usage."""
        if self.current_class and isinstance(node.func, ast.Name):
            name = node.func.id
            if name and name[0].isupper():
                self.type_usage.setdefault(self.current_class, set()).add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Collect names from ``from ... import ...`` statements."""
        for alias in node.names:
            name = alias.asname or alias.name
            self.import_map[name] = alias.name
        self.generic_visit(node)

    def visit_Import(self, node):
        """Collect names from ``import ...`` statements."""
        for alias in node.names:
            name = alias.asname or alias.name
            self.import_map[name] = alias.name
        self.generic_visit(node)
